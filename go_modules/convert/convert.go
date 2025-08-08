// go_modules/convert/convert.go
package main

import (
	"fmt"
	"go_modules/utils"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
)

func main() {
	if len(os.Args) < 3 {
		fmt.Println("Thiếu tham số: input_file output_file")
		os.Exit(1)
	}

	inputFile := os.Args[1]
	outputFile := os.Args[2]
	ffmpeg := utils.GetFFmpegPath()

	ext := strings.ToLower(filepath.Ext(outputFile))

	var args []string
	switch ext {
	case ".mov":
		// Remux MOV, bỏ stream Data (tmcd) cho sạch
		args = []string{
			"-hide_banner", "-y", "-i", inputFile,
			"-map", "0:v:0", "-map", "0:a?", "-map", "-0:d",
			"-c", "copy",
			outputFile,
		}

	case ".mp4":
		// ProRes/DNxHD -> H.264/AAC (convert 4:2:2 -> 4:2:0 trước khi NVENC)
		args = []string{
			"-hide_banner", "-y", "-i", inputFile,
			"-map", "0:v:0", "-map", "0:a?", "-map", "-0:d",
			"-vf", "format=yuv420p",
			"-c:v", "h264_nvenc", "-preset", "p2",
			"-c:a", "aac", "-b:a", "192k",
			"-movflags", "+faststart",
			outputFile,
		}

	default:
		// Đích lạ → transcode phổ thông
		args = []string{
			"-hide_banner", "-y", "-i", inputFile,
			"-map", "0:v:0", "-map", "0:a?",
			"-c:v", "h264_nvenc", "-preset", "p2",
			"-c:a", "aac", "-b:a", "192k",
			outputFile,
		}
	}

	fmt.Printf("🔄 Convert: %s --> %s\n", inputFile, outputFile)

	cmd := exec.Command(ffmpeg, args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}

	if err := cmd.Run(); err != nil {
		fmt.Println("❌ Lỗi Convert:", err)
		os.Exit(2)
	}

	fmt.Println("✅ Successfully:", outputFile)
}
