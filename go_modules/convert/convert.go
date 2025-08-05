// go_modules/convert/convert.go
package main

import (
	"fmt"
	"os"
	"os/exec"

	"go_modules/utils"
)

// Giữ nguyên import...
// Trả về đường dẫn tới ffmpeg trong thư mục assets
func main() {
	if len(os.Args) < 3 {
		fmt.Println("Thiếu tham số: input_file output_file")
		os.Exit(1)
	}

	inputFile := os.Args[1]
	outputFile := os.Args[2]
	ffmpeg := utils.GetFFmpegPath()

	fmt.Printf("🔄 Convert: %s --> %s\n", inputFile, outputFile)

	cmd := exec.Command(ffmpeg, "-y", "-i", inputFile, "-c:v", "copy", "-c:a", "copy", outputFile)

	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		fmt.Println("❌ Lỗi Convert:", err)
		os.Exit(2)
	}

	fmt.Println("✅ Successfully:", outputFile)
}
