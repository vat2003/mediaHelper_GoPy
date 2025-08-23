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
		fmt.Println("❌ Thiếu tham số: input_file output_file")
		fmt.Println("💡 Ví dụ: extractAudio.exe input.mp4 output.mp3")
		os.Exit(1)
	}

	inputFile := os.Args[1]
	outputFile := os.Args[2]

	ffmpeg := utils.GetFFmpegPath()
	ffprobe := utils.GetFFprobePath()

	// Lấy codec audio từ video
	codec, err := utils.GetAudioCodec(inputFile, ffprobe)
	if err != nil {
		fmt.Println("❌ Lỗi khi lấy codec audio:", err)
		os.Exit(2)
	}

	outputExt := strings.ToLower(filepath.Ext(outputFile))
	isCopy := utils.ShouldCopyCodec(codec, outputExt)

	var args []string
	if isCopy {
		args = []string{
			"-y", "-i", inputFile,
			"-map", "0:a:0?", "-vn", "-sn", "-dn", "-map", "-0:d",
			"-fflags", "+genpts", "-avoid_negative_ts", "make_zero",
			"-c:a", "copy",
		}
		switch outputExt {
		case ".mp4", ".m4a", ".mov":
			// an toàn cho AAC: chuyển ADTS → ASC nếu có
			args = append(args, "-bsf:a", "aac_adtstoasc", "-movflags", "+faststart")
		}
		args = append(args, outputFile)
	} else {
		enc := utils.GetTranscodeCodec(outputExt)
		args = []string{
			"-y", "-i", inputFile,
			"-map", "0:a:0?", "-vn", "-sn", "-dn", "-map", "-0:d",
			"-fflags", "+genpts", "-avoid_negative_ts", "make_zero",
			"-c:a", enc,
		}
		switch outputExt {
		case ".mp3":
			// CBR, đồng bộ: tránh VBR nếu bạn cần bitrate cố định
			args = append(args, "-b:a", "192k", "-ar", "48000", "-ac", "2", "-write_xing", "1")
		case ".mp4", ".m4a":
			args = append(args, "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart")
		case ".wav":
			args = append(args, "-ar", "48000", "-ac", "2") // PCM
		default:
			args = append(args, "-b:a", "192k", "-ar", "48000", "-ac", "2")
		}
		args = append(args, outputFile)
	}

	cmd := exec.Command(ffmpeg, args...)

	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	// Ẩn console window (chỉ có tác dụng trên Windows)
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
	if err := cmd.Run(); err != nil {
		fmt.Println("❌ Lỗi khi extract audio:", err)
		os.Exit(3)
	}

	fmt.Println("✅ Extract audio thành công:", outputFile)
}
