package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"

	"github.com/vat2003/mediaHelper_GoPy/go_modules/utils"
)

var mediaExts = map[string]bool{
	".mp4": true, ".mkv": true, ".mov": true, ".avi": true, ".flv": true,
	".mp3": true, ".wav": true, ".aac": true,
}

func isMediaFile(name string) bool {
	ext := strings.ToLower(filepath.Ext(name))
	return mediaExts[ext]
}

func main() {
	if len(os.Args) < 5 {
		fmt.Println("ERROR: Usage: loop_media.exe <input_file_or_folder> <output_file> <loop_count_or_minutes> <mode: count|duration>")
		os.Exit(1)
	}

	inputPath := os.Args[1]
	outputFile := os.Args[2]
	loopParam := os.Args[3]
	mode := os.Args[4] // "count" or "duration"

	ffmpeg := utils.GetFFmpegPath()
	ffprobe := utils.GetFFprobePath()

	// Nếu input là thư mục, tìm file media đầu tiên trong đó
	info, err := os.Stat(inputPath)
	if err != nil {
		fmt.Println("ERROR: Input không tồn tại:", err)
		os.Exit(1)
	}

	if info.IsDir() {
		entries, err := os.ReadDir(inputPath)
		if err != nil {
			fmt.Println("ERROR: Không thể đọc thư mục:", err)
			os.Exit(1)
		}
		found := ""
		for _, e := range entries {
			if !e.IsDir() && isMediaFile(e.Name()) {
				found = filepath.Join(inputPath, e.Name())
				break
			}
		}
		if found == "" {
			fmt.Println("ERROR: Không tìm thấy file media trong thư mục.")
			os.Exit(1)
		}
		inputPath = found
	}

	// Lấy đường dẫn tuyệt đối của file input
	inputAbs, err := filepath.Abs(inputPath)
	if err != nil {
		fmt.Println("ERROR: Không thể lấy đường dẫn tuyệt đối:", err)
		os.Exit(1)
	}

	// Xử lý loopCount
	var loopCount int
	switch mode {
	case "count":
		loopCount, err = strconv.Atoi(loopParam)
		if err != nil || loopCount <= 0 {
			fmt.Println("ERROR: Loop count phải là số nguyên > 0")
			os.Exit(1)
		}
	case "duration":
		// Lấy duration bằng ffprobe
		probeCmd := exec.Command(ffprobe, "-v", "error", "-show_entries", "format=duration",
			"-of", "default=noprint_wrappers=1:nokey=1", inputAbs)
		probeCmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
		out, err := probeCmd.Output()
		if err != nil {
			fmt.Println("ERROR: Không thể lấy thời lượng file:", err)
			os.Exit(1)
		}
		durationSec, _ := strconv.ParseFloat(strings.TrimSpace(string(out)), 64)
		minutes, err := strconv.ParseFloat(loopParam, 64)
		if err != nil || minutes <= 0 {
			fmt.Println("ERROR: Số phút phải > 0")
			os.Exit(1)
		}
		targetSeconds := minutes * 60
		loopCount = 1
		totalDuration := durationSec
		for totalDuration < targetSeconds {
			loopCount++
			totalDuration += durationSec
		}
		fmt.Printf("INFO: File gốc dài %.1f giây ➜ Lặp %d lần để đạt ≥ %.0f phút (%.1f giây)\n",
			durationSec, loopCount, minutes, totalDuration)
	default:
		fmt.Println("ERROR: Chế độ phải là 'count' hoặc 'duration'")
		os.Exit(1)
	}

	// Tạo concat list tạm với tên duy nhất theo PID
	concatList := filepath.Join(os.TempDir(), fmt.Sprintf("concat_list_%d.txt", os.Getpid()))
	f, err := os.Create(concatList)
	if err != nil {
		fmt.Println("ERROR: Không thể tạo concat list:", err)
		os.Exit(1)
	}
	defer func() {
		f.Close()
		os.Remove(concatList)
	}()

	// Chuyển backslash -> slash và escape dấu nháy đơn
	safePath := strings.ReplaceAll(inputAbs, "\\", "/")
	safePath = strings.ReplaceAll(safePath, "'", "'\\''")

	for i := 0; i < loopCount; i++ {
		// ghi dạng: file 'C:/path/to/file.mp4'
		_, err := fmt.Fprintf(f, "file '%s'\n", safePath)
		if err != nil {
			fmt.Println("ERROR: Lỗi khi ghi concat list:", err)
			os.Exit(1)
		}
	}
	// flush file
	if err := f.Sync(); err != nil {
		// không fatal, chỉ cảnh báo
		fmt.Println("INFO: Không thể sync file concat list:", err)
	}

	// Chạy ffmpeg
	// fmt.Println("INFO: Bắt đầu ffmpeg, output =", outputFile)
	ffCmd := exec.Command(ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", concatList, "-c", "copy", outputFile)
	ffCmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
	ffCmd.Stdout = os.Stdout
	ffCmd.Stderr = os.Stderr

	err = ffCmd.Run()
	if err != nil {
		// Nếu file tồn tại và có kích thước > 0 thì coi là cảnh báo (vẫn trả 0)
		if info, statErr := os.Stat(outputFile); statErr == nil && info.Size() > 0 {
			// fmt.Println("WARN: ffmpeg lỗi nhưng file đã được tạo:", err)
			os.Exit(0)
		} else {
			// fmt.Println("ERROR: ffmpeg thất bại:", err)
			os.Exit(1)
		}
	}

	// fmt.Println("INFO: DONE", outputFile)
	os.Exit(0)
}
