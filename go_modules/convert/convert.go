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
		// Bước 1: thử remux nhanh (copy)
		args = []string{
			"-hide_banner", "-y", "-i", inputFile,
			"-map", "0:v:0", "-map", "0:a?", "-map", "-0:d",
			"-c", "copy",
			outputFile,
		}

		// Chạy thử remux
		cmd := exec.Command(ffmpeg, args...)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}

		if err := cmd.Run(); err != nil {
			fmt.Println("⚠️ Remux thất bại → fallback sang encode...")

			// Bước 2: fallback encode (NVENC)
			args = []string{
				"-hide_banner", "-y", "-i", inputFile,
				"-map", "0:v:0", "-map", "0:a?", "-map", "-0:d",

				// Video NVENC
				"-c:v", "h264_nvenc",
				"-preset", "p4",
				"-profile:v", "high",
				"-level", "5.1",
				"-vf", "format=yuv420p",

				// Rate control
				"-rc", "vbr",
				"-cq", "23",
				"-b:v", "0",

				// Audio
				"-c:a", "aac",
				"-b:a", "192k",
				"-ar", "48000",
				"-ac", "2",

				// MOV container
				outputFile,
			}

			cmd = exec.Command(ffmpeg, args...)
			cmd.Stdout = os.Stdout
			cmd.Stderr = os.Stderr
			cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}

			if err := cmd.Run(); err != nil {
				fmt.Println("❌ Encode MOV thất bại:", err)
				os.Exit(2)
			}
		}

	case ".mp4":
		args = []string{
			"-hide_banner", "-y", "-i", inputFile,
			"-map", "0:v:0", "-map", "0:a?", "-map", "-0:d",

			// Video: NVENC + chất lượng cố định
			"-vf", "format=yuv420p", //Chuyển màu về YUV 4:2:0 (chuẩn bắt buộc để tương thích hầu hết player, YouTube/Facebook).
			"-c:v", "h264_nvenc",
			"-preset", "p4", //p1 nhanh nhất, p7 chậm nhưng chất lượng cao hơn
			"-profile:v", "high", //Profile H.264, hỗ trợ 8-bit 4:2:0, cần thiết cho streaming.
			"-level", "5.1", //Cho phép xử lý video 4K đến ~30fps.

			// Rate control: chất lượng cố định (CQ)
			"-rc", "vbr",
			"-cq", "23", // 15–23, số càng thấp càng đẹp
			"-b:v", "0", // để ffmpeg tự chọn bitrate phù hợp

			// Audio
			"-c:a", "aac",
			"-b:a", "132k",
			"-ar", "48000",
			"-ac", "2",

			// MP4 tối ưu streaming
			"-movflags", "+faststart",

			outputFile,
		}

	case ".flv":
		args = []string{
			"-hide_banner",
			"-y",
			"-i", inputFile,

			// Copy video/audio streams, không encode lại
			"-c:v", "copy",
			"-c:a", "copy",

			// Output FLV

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
