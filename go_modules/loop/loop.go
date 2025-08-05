package main

import (
	"fmt"
	"go_modules/utils"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
)

func main() {
	if len(os.Args) < 5 {
		fmt.Println("Usage: go run loop_media.go <input_file> <output_file> <loop_count_or_minutes> <mode: count|duration>")
		return
	}

	inputFile := os.Args[1]
	outputFile := os.Args[2]
	loopParam := os.Args[3]
	mode := os.Args[4] // "count" or "duration"
	ffmpeg := utils.GetFFmpegPath()
	ffprobe := utils.GetFFprobePath()

	// Create temp concat list file
	concatList := "concat_list.txt"
	inputAbs, _ := filepath.Abs(inputFile)

	var loopCount int
	var err error

	switch mode {
	case "count":
		loopCount, err = strconv.Atoi(loopParam)
		if err != nil || loopCount <= 0 {
			fmt.Println("Loop count phải là số nguyên > 0")
			return
		}
	case "duration":
		// Lấy duration của file input bằng ffprobe
		cmd := exec.Command(ffprobe, "-v", "error", "-show_entries", "format=duration",
			"-of", "default=noprint_wrappers=1:nokey=1", inputFile)
		out, err := cmd.Output()
		// Ẩn console window (chỉ có tác dụng trên Windows)
		cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
		if err != nil {
			fmt.Println("Không thể lấy thời lượng file:", err)
			return
		}

		durationSec, _ := strconv.ParseFloat(strings.TrimSpace(string(out)), 64)

		minutes, err := strconv.ParseFloat(loopParam, 64)
		if err != nil || minutes <= 0 {
			fmt.Println("Số phút phải > 0")
			return
		}

		targetSeconds := minutes * 60
		loopCount = 1
		totalDuration := durationSec

		for totalDuration < targetSeconds {
			loopCount++
			totalDuration += durationSec
		}
		fmt.Printf("⏱ File gốc dài %.1f giây ➜ Lặp %d lần để đạt ≥ %.0f phút (%.1f giây)\n",
			durationSec, loopCount, minutes, totalDuration)

	default:
		fmt.Println("Chế độ phải là 'count' hoặc 'duration'")
		return
	}

	// Ghi danh sách concat vào file tạm
	f, err := os.Create(concatList)
	if err != nil {
		fmt.Println("❌ Error creating concat list file:", err)
		return
	}
	defer os.Remove(concatList) // Xóa file tạm sau khi hoàn thành
	defer f.Close()

	for i := 0; i < loopCount; i++ {
		f.WriteString(fmt.Sprintf("file '%s'\n", inputAbs))
	}

	// Gọi ffmpeg để nối các file
	cmd := exec.Command(ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", concatList, "-c", "copy", outputFile)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	// Ẩn console window (chỉ có tác dụng trên Windows)
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
	fmt.Println("FFmpeg cmd:", strings.Join(cmd.Args, " "))

	fmt.Println("🚀 Đang tạo file lặp...")
	err = cmd.Run()
	if err != nil {
		fmt.Println("❌ Lỗi ffmpeg:", err)
		return
	}
	fmt.Println("✅ Hoàn tất:", outputFile)
}
