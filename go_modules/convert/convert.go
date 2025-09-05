// go_modules/convert/convert.go
package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"

	"github.com/vat2003/mediaHelper_GoPy/go_modules/utils"
)

func main() {
	if len(os.Args) < 3 {
		fmt.Println("Thiếu tham số: input_file output_file")
		os.Exit(1)
	}

	inputFile := os.Args[1]
	outputFile := os.Args[2]
	// Nếu output có dạng ...".flv-xxx", thì đổi thành "...-xxx.flv"
	if strings.Contains(outputFile, ".flv-") {
		parts := strings.Split(outputFile, ".flv-")
		outputFile = parts[0] + "-" + parts[1] + ".flv"
	}
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

	case ".flv-fullhd-24":
		args = []string{
			"-hide_banner", "-y", "-i", inputFile,
			"-map", "0:v:0", "-map", "0:a?", "-map", "-0:d",

			"-vf", "format=yuv420p",
			"-c:v", "h264_nvenc",
			"-preset", "p2",
			"-profile:v", "high",
			"-level", "4.1",

			"-rc", "cbr",
			"-b:v", "4500k",
			"-maxrate", "4500k",
			"-bufsize", "9000k",
			"-g", "48",

			"-c:a", "aac",
			"-b:a", "160k",
			"-ar", "48000",
			"-ac", "2",

			"-f", "flv", outputFile,
		}

	case ".flv-4k-24":
		args = []string{
			"-hide_banner", "-y", "-i", inputFile,
			"-map", "0:v:0", "-map", "0:a?", "-map", "-0:d",

			"-vf", "format=yuv420p",
			"-c:v", "h264_nvenc",
			"-preset", "p2",
			"-profile:v", "high",
			"-level", "5.1",

			"-rc", "cbr",
			"-b:v", "15000k",
			"-maxrate", "15000k",
			"-bufsize", "30000k",
			"-g", "48",

			"-c:a", "aac",
			"-b:a", "160k",
			"-ar", "48000",
			"-ac", "2",

			"-f", "flv", outputFile,
		}

	case ".flv-4k-30":
		args = []string{
			"-hide_banner", "-y", "-i", inputFile,
			"-map", "0:v:0", "-map", "0:a?", "-map", "-0:d",

			"-vf", "format=yuv420p",
			"-c:v", "h264_nvenc",
			"-preset", "p2",
			"-profile:v", "high",
			"-level", "5.1",

			"-rc", "cbr",
			"-b:v", "18000k",
			"-maxrate", "18000k",
			"-bufsize", "36000k",
			"-g", "60",

			"-c:a", "aac",
			"-b:a", "160k",
			"-ar", "48000",
			"-ac", "2",

			"-f", "flv", outputFile,
		}

	case ".flv-4k-60":
		args = []string{
			"-hide_banner", "-y", "-i", inputFile,
			"-map", "0:v:0", "-map", "0:a?", "-map", "-0:d",

			"-vf", "format=yuv420p",
			"-c:v", "h264_nvenc",
			"-preset", "p2",
			"-profile:v", "high",
			"-level", "5.2",

			"-rc", "cbr",
			"-b:v", "25000k",
			"-maxrate", "25000k",
			"-bufsize", "50000k",
			"-g", "120",

			"-c:a", "aac",
			"-b:a", "160k",
			"-ar", "48000",
			"-ac", "2",

			"-f", "flv", outputFile,
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
