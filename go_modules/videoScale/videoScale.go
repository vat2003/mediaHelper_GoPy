package main

import (
	"fmt"
	"go_modules/utils"
	"log"
	"os"
	"os/exec"
	"strconv"
	"strings"
)

func main() {
	if len(os.Args) < 5 {
		fmt.Println("Usage: go run videoScale.go <input_video> <output_file> <resolution> <cpu|gpu> [video_bitrate] [fps] [audio_bitrate] [preset]")
		return
	}

	inputVideo := os.Args[1]
	outputFile := os.Args[2]
	resolution := os.Args[3]
	processor := os.Args[4] // cpu or gpu

	videoBitrate := "3000k"
	if len(os.Args) >= 6 && os.Args[5] != "" {
		videoBitrate = os.Args[5]
	}

	fps := 0
	if len(os.Args) >= 7 && os.Args[6] != "" {
		var err error
		fps, err = strconv.Atoi(os.Args[6])
		if err != nil || fps < 0 {
			log.Fatalf("❌ FPS không hợp lệ: %s", os.Args[6])
		}
	}

	audioBitrate := "128k"
	if len(os.Args) >= 8 && os.Args[7] != "" {
		audioBitrate = os.Args[7]
	}

	preset := "medium"
	if len(os.Args) >= 9 && os.Args[8] != "" {
		preset = os.Args[8]
	}

	ffmpeg := utils.GetFFmpegPath()

	// Scale filter
	var scaleFilter string
	if fps > 0 {
		scaleFilter = fmt.Sprintf("fps=%d,scale=%s,format=yuv420p", fps, resolution)
	} else {
		scaleFilter = fmt.Sprintf("scale=%s,format=yuv420p", resolution)
		fmt.Println("⚠️ FPS không được đặt, sử dụng mặc định.")
	}

	// FFmpeg arguments
	ffmpegArgs := []string{
		"-i", inputVideo,
		"-vf", scaleFilter,
		"-c:v", "libx264", // default dùng CPU
		"-preset", preset,
		"-b:v", videoBitrate,
		"-c:a", "aac",
		"-b:a", audioBitrate,
		"-pix_fmt", "yuv420p",
		outputFile,
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

	fmt.Println("🚀 Đang scale video...")
	fmt.Println("FFmpeg command:", strings.Join(cmd.Args, " "))

	if err := cmd.Run(); err != nil {
		log.Fatal("❌ Lỗi khi chạy ffmpeg:", err)
	}

	fmt.Println("✅ Video đã được scale thành công:", outputFile)
}
