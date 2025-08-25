// concat_from_paths.go
// Build: go build -o go_concatPaths.exe concat_from_paths.go
//
// Cách dùng:
// 1) Truyền trực tiếp đường dẫn theo thứ tự cần ghép:
//    go_concatPaths.exe "<output_folder>" "E:\A.mp4" "E:\B.mp4" "E:\C.mp3"
//
// 2) Hoặc truyền một file danh sách (.txt), mỗi dòng 1 path (có thể kèm dấu "):
//    go_concatPaths.exe "<output_folder>" "E:\list.txt"
//
// Ghi chú:
// - Tự tạo <output_folder>\{timestamp}_output.<ext>
// - Nếu nhiều đuôi: chọn đuôi phổ biến nhất; nếu vừa có video vừa có audio → .mp4
// - Dùng ffmpeg concat demuxer với -c copy (không re-encode)

package main

import (
	"bufio"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"syscall"
	"time"

	"github.com/vat2003/mediaHelper_GoPy/go_modules/utils"
)

var videoExts = []string{".mp4", ".avi", ".mkv", ".mov", ".flv"}
var audioExts = []string{".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"}
var mediaExts = append(videoExts, audioExts...)

func main() {
	if len(os.Args) < 3 {
		fmt.Println("Usage:")
		fmt.Println("  go_concatPaths.exe <output_folder> <path_or_list.txt> [<path2> <path3> ...]")
		return
	}

	outputFolder := os.Args[1]
	args := os.Args[2:]

	paths, err := resolveInputPaths(args)
	if err != nil {
		fmt.Println("❌", err)
		return
	}
	if len(paths) == 0 {
		fmt.Println("❌ Không có đường dẫn hợp lệ để ghép.")
		return
	}

	// Lọc giữ file hợp lệ & là media
	var files []string
	for _, p := range paths {
		if fileExists(p) && isMediaFile(p) {
			files = append(files, p)
		}
	}
	if len(files) == 0 {
		fmt.Println("❌ Không có file media hợp lệ.")
		return
	}

	if err := os.MkdirAll(outputFolder, os.ModePerm); err != nil {
		fmt.Println("❌ Không tạo được thư mục output:", err)
		return
	}

	if err := concatFromPaths(files, outputFolder); err != nil {
		fmt.Println("❌ Lỗi concat:", err)
	}
}

func resolveInputPaths(args []string) ([]string, error) {
	// Nếu chỉ 1 tham số và là .txt → đọc từ file
	if len(args) == 1 && strings.HasSuffix(strings.ToLower(args[0]), ".txt") {
		return readPathsFromFile(args[0])
	}
	// Ngược lại: coi mọi arg là một path
	cleaned := make([]string, 0, len(args))
	for _, p := range args {
		p = strings.TrimSpace(p)
		p = strings.Trim(p, "\"")
		if p != "" {
			cleaned = append(cleaned, p)
		}
	}
	return cleaned, nil
}

func readPathsFromFile(listPath string) ([]string, error) {
	f, err := os.Open(listPath)
	if err != nil {
		return nil, fmt.Errorf("không mở được file danh sách: %v", err)
	}
	defer f.Close()

	var paths []string
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		line = strings.Trim(line, "\"") // bỏ dấu " nếu có
		if line == "" {
			continue
		}
		paths = append(paths, line)
	}
	if err := sc.Err(); err != nil {
		return nil, fmt.Errorf("lỗi đọc file danh sách: %v", err)
	}
	return paths, nil
}

func isMediaFile(path string) bool {
	ext := strings.ToLower(filepath.Ext(path))
	for _, e := range mediaExts {
		if ext == e {
			return true
		}
	}
	return false
}

func fileExists(path string) bool {
	st, err := os.Stat(path)
	return err == nil && !st.IsDir()
}

func concatFromPaths(files []string, outputFolder string) error {
	if len(files) == 0 {
		return errors.New("danh sách file trống")
	}

	ext := getOutputExtension(files)
	ts := time.Now().UnixNano()
	outputBase := fmt.Sprintf("%d_output", ts)
	outputPath := filepath.Join(outputFolder, outputBase+ext)
	tempListPath := filepath.Join(os.TempDir(), fmt.Sprintf("temp_list_%d.txt", ts))

	if err := createTempConcatList(files, tempListPath); err != nil {
		return fmt.Errorf("không thể tạo danh sách tạm: %w", err)
	}

	fmt.Println("🚀 Bắt đầu ghép:", outputPath)
	if err := runFFmpegConcat(tempListPath, outputPath); err != nil {
		_ = os.Remove(tempListPath)
		return err
	}
	_ = os.Remove(tempListPath)

	fmt.Println("✅ Hoàn tất:", outputPath)
	return nil
}

func runFFmpegConcat(listPath, outputPath string) error {
	ffmpeg := utils.GetFFmpegPath()
	args := []string{
		"-hide_banner",
		"-fflags", "+genpts",
		"-f", "concat", "-safe", "0",
		"-i", listPath,
		"-c", "copy",
		"-y", outputPath,
	}

	cmd := exec.Command(ffmpeg, args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	// Ẩn console trên Windows
	if runtime.GOOS == "windows" {
		cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
	}

	return cmd.Run()
}

func createTempConcatList(files []string, path string) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()

	w := bufio.NewWriter(f)
	for _, file := range files {
		abs, err := filepath.Abs(file)
		if err != nil {
			return err
		}
		// Escape cho concat demuxer
		escaped := strings.ReplaceAll(abs, "\\", "\\\\")
		escaped = strings.ReplaceAll(escaped, "'", "'\\''")
		if _, err := w.WriteString(fmt.Sprintf("file '%s'\n", escaped)); err != nil {
			return err
		}
	}
	return w.Flush()
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

	// Nếu tất cả cùng đuôi → dùng luôn
	if len(extCount) == 1 {
		for e := range extCount {
			return e
		}
	}

	// Chọn đuôi phổ biến
	maxCount := 0
	chosen := ".mp4"
	for e, c := range extCount {
		if c > maxCount {
			maxCount = c
			chosen = e
		}
	}
	// Nếu có cả video & audio → .mp4
	if hasVideo && hasAudio {
		return ".mp4"
	}
	return chosen
}

func contains(slice []string, s string) bool {
	for _, e := range slice {
		if s == e {
			return true
		}
	}
	return false
}
