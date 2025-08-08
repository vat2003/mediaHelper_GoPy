package main

import (
	"fmt"
	"go_modules/utils"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
)

func getDuration(input string) (float64, error) {
	ffprobe := utils.GetFFprobePath()
	cmd := exec.Command(ffprobe, "-v", "error", "-show_entries", "format=duration",
		"-of", "default=noprint_wrappers=1:nokey=1", input)
	output, err := cmd.Output()
	if err != nil {
		return 0, err
	}
	durationStr := strings.TrimSpace(string(output))
	return strconv.ParseFloat(durationStr, 64)
}
func main() {
	if len(os.Args) < 7 {
		fmt.Println("Usage: go run mergeMedia.go <input_video_or_image> <input_audio> <output_file> <resolution> <cpu|gpu> <output_duration_seconds> [bitrate] [fps (0 = default)]")
		return
	}

	inputVideoImage := os.Args[1]
	inputAudio := os.Args[2]
	outputFile := os.Args[3]
	resolution := os.Args[4]
	processor := os.Args[5]
	outputDurationStr := os.Args[6]
	ffmpeg := utils.GetFFmpegPath()
	fmt.Println("FFmpeg path:", ffmpeg)

	// Lấy bitrate mặc định nếu không truyền
	bitrate := "1500k"
	if len(os.Args) >= 8 && os.Args[7] != "" {
		bitrate = os.Args[7]
	}

	// Lấy fps mặc định nếu không truyền
	fps := 0
	if len(os.Args) >= 9 && os.Args[8] != "" {
		var err error
		fps, err = strconv.Atoi(os.Args[8])
		if err != nil || fps < 0 {
			log.Fatalf("❌ FPS không hợp lệ: %s", os.Args[8])
		}
	}

	// Parse output duration
	outputDuration, err := strconv.ParseFloat(outputDurationStr, 64)
	if err != nil || outputDuration < 0 {
		log.Fatalf("❌ Output duration không hợp lệ: %s", outputDurationStr)
	}

	// Nếu không nhập thời lượng → dùng audio gốc
	if outputDuration == 0 {
		fmt.Println("🔍 Đang lấy duration của audio...")
		outputDuration, err = getDuration(inputAudio)
		if err != nil {
			log.Fatalf("❌ Lỗi khi lấy duration của audio: %v", err)
		}
		fmt.Printf("⏱️ Duration của audio: %.2f giây\n", outputDuration)
	}

	// Kiểm tra input là ảnh hay video
	ext := strings.ToLower(filepath.Ext(inputVideoImage))
	isImage := ext == ".jpg" || ext == ".jpeg" || ext == ".png" || ext == ".bmp" || ext == ".webp"

	// Tạo filter scale
	var scaleFilter string
	if fps > 0 {
		scaleFilter = fmt.Sprintf("fps=%d,scale=%s", fps, resolution)
	} else {
		fmt.Println("⚠️ FPS không được đặt, sử dụng mặc định của FFmpeg.")
		scaleFilter = fmt.Sprintf("scale=%s", resolution)
	}

	var ffmpegArgs []string
	var videoCodec string
	var preset string

	// Chọn codec và preset tùy theo CPU hoặc GPU
	if processor == "gpu" {
		videoCodec = "h264_nvenc"
		preset = "p4" // preset chất lượng cao cho GPU (có thể dùng: p1 (nhanh) đến p7 (chất lượng cao))
	} else {
		videoCodec = "libx264"
		preset = "ultrafast" // preset nhanh cho CPU
	}

	if isImage {
		// Với ảnh: lặp ảnh -> tạo video
		ffmpegArgs = []string{
			"-loop", "1",
			"-i", inputVideoImage,
			"-stream_loop", "-1",
			"-i", inputAudio,
			"-t", fmt.Sprintf("%.2f", outputDuration),
			"-vf", scaleFilter,
			"-map", "0:v:0",
			"-map", "1:a:0",
			"-c:v", videoCodec,
			"-preset", preset,
			"-b:v", bitrate,
			"-c:a", "aac",
			"-shortest",
			outputFile,
		}
	} else {
		// Với video: lặp video, loại bỏ audio gốc
		ffmpegArgs = []string{
			"-stream_loop", "-1",
			"-i", inputVideoImage,
			"-stream_loop", "-1",
			"-i", inputAudio,
			"-t", fmt.Sprintf("%.2f", outputDuration),
			"-vf", scaleFilter,
			"-map", "0:v:0",
			"-map", "1:a:0",
			"-c:v", videoCodec,
			"-preset", preset,
			"-b:v", bitrate,
			"-c:a", "aac",
			"-shortest",
			outputFile,
		}
	}

	// Nếu dùng GPU, thêm các thông số kỹ thuật cho NVIDIA
	if processor == "gpu" {
		// Chèn thêm thông số trước codec (nếu cần)
		// Thêm vào cuối lệnh: bạn cũng có thể thêm tune, rc, profile nếu muốn
		extraGpuArgs := []string{
			"-rc", "vbr",            // Rate control: vbr (Variable Bitrate)
			"-cq", "19",             // Constant Quality, nhỏ hơn = chất lượng cao hơn
			"-bf", "2",              // B-frames
			"-g", "60",              // GOP size
			"-movflags", "+faststart", // Tối ưu phát trực tuyến
		}
		ffmpegArgs = append(ffmpegArgs[:len(ffmpegArgs)-1], extraGpuArgs...)
		ffmpegArgs = append(ffmpegArgs, outputFile)
	}


	cmd := exec.Command(ffmpeg, append([]string{"-y"}, ffmpegArgs...)...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	// Ẩn console window (chỉ có tác dụng trên Windows)
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}

	fmt.Println("🚀 Ghép video/audio...")
	fmt.Println("FFmpeg command:", strings.Join(cmd.Args, " "))

	if err := cmd.Run(); err != nil {
		fmt.Printf("❌ Lỗi khi chạy FFmpeg (%s): %v\n", cmd.String(), err)
		return
	}

	fmt.Println("✅ Thành công:", outputFile)
}
