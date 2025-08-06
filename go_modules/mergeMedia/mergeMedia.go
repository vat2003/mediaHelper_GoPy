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
		scaleFilter = fmt.Sprintf("fps=%d,scale=%s,format=yuv420p", fps, resolution)
	} else {
		fmt.Println("⚠️ FPS không được đặt, sử dụng mặc định của FFmpeg.")
		scaleFilter = fmt.Sprintf("scale=%s,format=yuv420p", resolution)
	}

	var ffmpegArgs []string

	if isImage {
		// Với ảnh: lặp ảnh -> tạo video
		ffmpegArgs = []string{
			"-loop", "1",
			"-i", inputVideoImage,
			"-stream_loop", "-1",
			"-i", inputAudio,
			"-t", fmt.Sprintf("%.2f", outputDuration),
			"-vf", scaleFilter,
			"-c:v", "libx264",
			"-preset", "ultrafast",
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
			"-map", "0:v:0", // chỉ lấy video từ input 0
			"-map", "1:a:0", // chỉ lấy audio từ input 1
			"-c:v", "libx264",
			"-preset", "fast",
			"-b:v", bitrate,
			"-c:a", "aac",
			"-shortest",
			outputFile,
		}
	}

	// Nếu dùng GPU
	if processor == "gpu" {
		for i := range ffmpegArgs {
			if ffmpegArgs[i] == "libx264" {
				ffmpegArgs[i] = "h264_nvenc"
			}
		}
	}

	cmd := exec.Command(ffmpeg, append([]string{"-y"}, ffmpegArgs...)...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	// Ẩn console window (chỉ có tác dụng trên Windows)
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}

	fmt.Println("🚀 Ghép video/audio...")
	fmt.Println("FFmpeg command:", strings.Join(cmd.Args, " "))

	if err := cmd.Run(); err != nil {
		fmt.Println("❌ Lỗi khi chạy ffmpeg:", err)
		return
	}

	fmt.Println("✅ Thành công:", outputFile)
}
