package main

import (
	"bufio"
	"fmt"
	"math/rand"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/vat2003/mediaHelper_GoPy/go_modules/utils"
)

var videoExts = []string{".mp4", ".avi", ".mkv", ".mov", ".flv"}
var audioExts = []string{".mp3", ".wav", ".aac"}
var mediaExts = append(videoExts, audioExts...)

func isMediaFile(filename string) bool {
	ext := strings.ToLower(filepath.Ext(filename))
	for _, e := range mediaExts {
		if ext == e {
			return true
		}
	}
	return false
}

func getMediaFiles(folder string) ([]string, error) {
	files, err := os.ReadDir(folder)
	if err != nil {
		return nil, err
	}

	var mediaFiles []string
	for _, file := range files {
		if !file.IsDir() && isMediaFile(file.Name()) {
			mediaFiles = append(mediaFiles, filepath.Join(folder, file.Name()))
		}
	}
	return mediaFiles, nil
}

func getDuration(file string) float64 {
	ffprobe := utils.GetFFprobePath()
	cmd := exec.Command(ffprobe, "-v", "error", "-show_entries", "format=duration",
		"-of", "default=noprint_wrappers=1:nokey=1", file)
	// Ẩn console window (chỉ có tác dụng trên Windows)
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
	out, err := cmd.Output()
	if err != nil {
		fmt.Printf("⚠️ Lỗi ffprobe: %v - file: %s\n", err, file)
		return 0
	}
	var duration float64
	fmt.Sscanf(string(out), "%f", &duration)
	return duration
}

func secondsToHHMMSS(seconds float64) string {
	hours := int(seconds / 3600)
	minutes := int((seconds - float64(hours*3600)) / 60)
	secs := int(seconds) % 60
	return fmt.Sprintf("%02d:%02d:%02d", hours, minutes, secs)
}

func createTracklist(files []string, tracklistPath string) {
	f, err := os.Create(tracklistPath)
	if err != nil {
		fmt.Println("❌ Error creating tracklist file:", err)
		return
	}
	defer f.Close()

	writer := bufio.NewWriter(f)
	currentTime := 0.0

	for _, file := range files {
		absPath, err := filepath.Abs(file)
		if err != nil {
			fmt.Println("⚠️ Lỗi lấy đường dẫn tuyệt đối:", err)
			continue
		}

		duration := getDuration(absPath)
		if duration <= 0 {
			fmt.Printf("⚠️ Không thể lấy thời lượng từ: %s\n", absPath)
			continue
		}

		base := strings.TrimSuffix(filepath.Base(file), filepath.Ext(file))
		line := fmt.Sprintf("[%s] %s\n", secondsToHHMMSS(currentTime), base)
		writer.WriteString(line)

		currentTime += duration
	}

	writer.Flush()
	fmt.Println("Tracklist đã được tạo:", tracklistPath)
}

func createTempConcatList(files []string, path string) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()
	writer := bufio.NewWriter(f)
	for _, file := range files {
		abs, err := filepath.Abs(file)
		if err != nil {
			return err
		}
		// Escape dấu \ và ' cho ffmpeg
		escaped := strings.ReplaceAll(abs, "\\", "\\\\")
		escaped = strings.ReplaceAll(escaped, "'", "'\\''")
		writer.WriteString(fmt.Sprintf("file '%s'\n", escaped))
	}
	return writer.Flush()
}

func concatMedia(inputFolder, outputFolder string, filesPerGroup int) {
	mediaFiles, err := getMediaFiles(inputFolder)
	if err != nil {
		fmt.Println("❌ Lỗi đọc thư mục:", err)
		return
	}

	if len(mediaFiles) == 0 {
		fmt.Println("❌ Không có file media nào trong thư mục.")
		return
	}

	os.MkdirAll(outputFolder, os.ModePerm)

	timestamp := time.Now().UnixNano() // Sử dụng nano giây để đảm bảo duy nhất

	// Shuffle và chọn filesPerGroup file
	shuffled := append([]string(nil), mediaFiles...)
	rand.Shuffle(len(shuffled), func(i, j int) {
		shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
	})
	selected := shuffled[:filesPerGroup]

	ext := getOutputExtension(selected)

	outputBase := fmt.Sprintf("%d_output", (timestamp))
	outputPath := filepath.Join(outputFolder, outputBase+ext)
	tracklistPath := filepath.Join(outputFolder, outputBase+"_tracklist.txt")
	tempListPath := filepath.Join(os.TempDir(), fmt.Sprintf("temp_list_%d.txt", timestamp))

	if err := createTempConcatList(selected, tempListPath); err != nil {
		fmt.Println("❌ Không thể tạo danh sách file tạm:", err)
		return
	}

	ffmpeg := utils.GetFFmpegPath()
	cmd := exec.Command(ffmpeg, "-hide_banner", "-fflags", "+genpts",
		"-f", "concat", "-safe", "0", "-i", tempListPath,
		"-c", "copy", "-y", outputPath)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}

	fmt.Println("🚀 Đang xử lý:", outputPath)
	if err := cmd.Run(); err != nil {
		fmt.Println("❌ Lỗi khi ghép file:", err)
		return
	}

	createTracklist(selected, tracklistPath)
	os.Remove(tempListPath)

	fmt.Println("✅ Xong:", outputPath)
}

func getOutputExtension(files []string) string {
	extCount := make(map[string]int)
	hasVideo, hasAudio := false, false

	for _, file := range files {
		ext := strings.ToLower(filepath.Ext(file))
		extCount[ext]++
		if contains(videoExts, ext) {
			hasVideo = true
		}
		if contains(audioExts, ext) {
			hasAudio = true
		}
	}

	if len(extCount) == 1 {
		for e := range extCount {
			return e
		}
	}

	maxCount := 0
	var ext string
	for e, count := range extCount {
		if count > maxCount {
			maxCount = count
			ext = e
		}
	}
	if hasVideo && hasAudio {
		return ".mp4"
	}
	return ext
}

func contains(slice []string, s string) bool {
	for _, e := range slice {
		if s == e {
			return true
		}
	}
	return false
}

func main() {
	if len(os.Args) != 4 {
		fmt.Println("Usage: go run random_concat.go <input_folder> <output_folder> <files_per_group>")
		return
	}

	inputFolder := os.Args[1]
	outputFolder := os.Args[2]
	filesPerGroup := atoi(os.Args[3])

	// 🟡 NEW: Nếu filesPerGroup = 0 thì dùng toàn bộ số file trong thư mục
	if filesPerGroup == 0 {
		allFiles, err := getMediaFiles(inputFolder)
		if err != nil {
			fmt.Println("❌ Không thể đọc file từ thư mục:", err)
			return
		}
		filesPerGroup = len(allFiles)
		fmt.Printf("📦 Input File Count = 0 => Dùng toàn bộ %d file\n", filesPerGroup)
	}

	concatMedia(inputFolder, outputFolder, filesPerGroup)
}

func atoi(s string) int {
	i, err := strconv.Atoi(s)
	if err != nil || i < 0 {
		fmt.Printf("Lỗi: %s phải là số nguyên >= 0\n", s)
		os.Exit(1)
	}
	return i
}
