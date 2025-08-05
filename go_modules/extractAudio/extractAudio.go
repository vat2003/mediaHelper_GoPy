package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"

	"go_modules/utils"
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

	outputExt := filepath.Ext(outputFile)

	var cmd *exec.Cmd
	if utils.ShouldCopyCodec(codec, outputExt) {
		fmt.Printf("🎧 Extract audio (copy): %s → %s\n", inputFile, outputFile)
		cmd = exec.Command(ffmpeg, "-y", "-i", inputFile, "-map", "a", "-c:a", "copy", outputFile)
	} else {
		selectedCodec := utils.GetTranscodeCodec(outputExt)
		fmt.Printf("🎧 Extract audio (transcode %s → %s): %s → %s\n", codec, selectedCodec, inputFile, outputFile)
		cmd = exec.Command(ffmpeg, "-y", "-i", inputFile, "-map", "a", "-c:a", selectedCodec, outputFile)
	}

	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		fmt.Println("❌ Lỗi khi extract audio:", err)
		os.Exit(3)
	}

	fmt.Println("✅ Extract audio thành công:", outputFile)
}
