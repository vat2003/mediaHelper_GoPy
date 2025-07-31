package main

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
)

func getDuration(input string) (float64, error) {
	cmd := exec.Command("ffprobe", "-v", "error", "-show_entries", "format=duration",
		"-of", "default=noprint_wrappers=1:nokey=1", input)
	output, err := cmd.Output()
	if err != nil {
		return 0, err
	}
	durationStr := strings.TrimSpace(string(output))
	return strconv.ParseFloat(durationStr, 64)
}

func main() {
	if len(os.Args) < 6 {
		fmt.Println("Usage: go run mergeMedia.go <input_video_or_image> <input_audio> <output_file> <resolution> <cpu|gpu>")
		return
	}

	inputVideoImage := os.Args[1]
	inputAudio := os.Args[2]
	outputFile := os.Args[3]
	resolution := os.Args[4] // "1920x1080" etc.
	processor := os.Args[5]  // "cpu" or "gpu"

	// Get audio duration
	audioDuration, err := getDuration(inputAudio)
	if err != nil {
		fmt.Println("❌ Lỗi khi lấy thời lượng audio:", err)
		return
	}

	// Determine if input is image or video
	ext := strings.ToLower(filepath.Ext(inputVideoImage))
	isImage := ext == ".jpg" || ext == ".jpeg" || ext == ".png" || ext == ".bmp" || ext == ".webp"

	var ffmpegArgs []string
	parts := strings.Split(resolution, "x")
	if len(parts) != 2 {
		log.Fatalf("Resolution không hợp lệ: %s", resolution)
	}
	// width := parts[0]
	// height := parts[1]

	scale_filter := "scale={self.resolution},format=yuv420p"

	if isImage {
		// Convert image to video that loops for the duration of audio
		ffmpegArgs = []string{
			"-loop", "1",
			"-i", inputVideoImage,
			"-i", inputAudio,
			"-t", fmt.Sprintf("%.2f", audioDuration),
			"-vf", scale_filter,
			"-c:v", "h264_nvenc",
			"-c:v", "libx264",
			"-preset", "fast",
			"-crf", "23",
			"-c:a", "aac",
			"-shortest",
			outputFile,
		}
	} else {
		// Loop video to match audio duration
		ffmpegArgs = []string{
			"-stream_loop", "-1",
			"-i", inputVideoImage,
			"-i", inputAudio,
			"-t", fmt.Sprintf("%.2f", audioDuration),
			"-vf", scale_filter,
			"-map", "0:v:0", // chỉ lấy video từ input 0
			"-map", "1:a:0", // chỉ lấy audio từ input 1
			"-c:v", "libx264",
			"-preset", "fast",
			"-crf", "23",
			"-c:a", "aac",
			"-shortest",
			outputFile,
		}
	}

	// Optional: Use GPU if selected
	if processor == "gpu" {
		// You may need to adjust codec depending on your GPU (e.g., h264_nvenc)
		for i, arg := range ffmpegArgs {
			if arg == "libx264" {
				ffmpegArgs[i] = "h264_nvenc"
				break
			}
		}
	}

	// Run ffmpeg
	cmd := exec.Command("ffmpeg", append([]string{"-y"}, ffmpegArgs...)...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	fmt.Println("🚀 Đang ghép video/audio...")
	fmt.Println("FFmpeg command:", strings.Join(cmd.Args, " "))

	if err := cmd.Run(); err != nil {
		fmt.Println("❌ Lỗi khi chạy ffmpeg:", err)
		return
	}

	fmt.Println("✅ Ghép thành công:", outputFile)
}
