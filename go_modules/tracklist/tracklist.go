package main

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Thiếu tham số: đường dẫn đến file .txt chứa danh sách video")
		return
	}

	inputTxtPath := os.Args[1]
	outputPath := "tracklist.txt"

	if len(os.Args) >= 3 {
		outputPath = os.Args[2]
	}

	lines, err := readLines(inputTxtPath)
	if err != nil {
		fmt.Println("Không thể đọc file: ", err)
		return
	}

	var tracklist []string
	totalSeconds := 0

	for _, line := range lines {
		filePath := strings.Trim(strings.TrimSpace(line), "\"") // xóa khoảng trắng và dấu ngoặc kép
		timestamp := secondsToHHMMSS(totalSeconds)
		title := strings.TrimSuffix(filepath.Base(filePath), filepath.Ext(filePath))

		if _, err := os.Stat(filePath); os.IsNotExist(err) {
			tracklist = append(tracklist, fmt.Sprintf("%s %s (File not found)", timestamp, title))
			continue
		}

		duration, err := getDurationInSeconds(filePath)
		if err != nil {
			tracklist = append(tracklist, fmt.Sprintf("%s %s (Lỗi đọc thời lượng)", timestamp, title))
			continue
		}

		tracklist = append(tracklist, fmt.Sprintf("%s %s", timestamp, title))
		totalSeconds += duration
	}

	err = os.WriteFile(outputPath, []byte(strings.Join(tracklist, "\n")), 0644)
	if err != nil {
		fmt.Println("Không thể ghi file: ", err)
		return
	}

	fmt.Println("Tracklist đã tạo tại: ", outputPath)
}

// Đọc từng dòng trong file .txt
func readLines(path string) ([]string, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var lines []string
	scanner := bufio.NewScanner(file)

	for scanner.Scan() {
		text := scanner.Text()
		if strings.TrimSpace(text) != "" {
			lines = append(lines, text)
		}
	}

	return lines, scanner.Err()
}

// Gọi ffprobe để lấy thời lượng
func getDurationInSeconds(filePath string) (int, error) {
	cmd := exec.Command("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filePath)

	output, err := cmd.Output()
	if err != nil {
		return 0, err
	}

	trimmed := strings.TrimSpace(string(output))
	duration, err := strconv.ParseFloat(trimmed, 64)
	if err != nil {
		return 0, err
	}

	return int(duration), nil
}

// Chuyển giây sang định dạng [HH:MM:SS]
func secondsToHHMMSS(seconds int) string {
	h := seconds / 3600
	m := (seconds % 3600) / 60
	s := seconds % 60
	return fmt.Sprintf("%02d:%02d:%02d", h, m, s)
}
