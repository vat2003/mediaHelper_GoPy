package main

import (
	"bufio"
	"fmt"
	"go_modules/utils"
	"math/rand"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"
)

var videoExts = []string{".mp4", ".avi", ".mkv", ".mov", ".flv"}
var audioExts = []string{".mp3", ".wav", ".aac"}
var mediaExts = append(videoExts, audioExts...)

func isMedaFile(filename string) bool {
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
		if !file.IsDir() && isMedaFile(file.Name()) {
			mediaFiles = append(mediaFiles, filepath.Join(folder, file.Name()))
		}
	}
	return mediaFiles, nil
}

func getDuration(file string) float64 {
	ffprobe := utils.GetFFprobePath()
	cmd := exec.Command(ffprobe, "-v", "error", "-show_entries", "format=duration",
		"-of", "default=noprint_wrappers=1:nokey=1", file)
	out, err := cmd.Output()
	// Ẩn console window (chỉ có tác dụng trên Windows)
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
	if err != nil {
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
		line := fmt.Sprintf("%s %s\n", secondsToHHMMSS(currentTime), base)
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
		writer.WriteString(fmt.Sprintf("file '%s'\n", escaped))
	}
	return writer.Flush()
}

func concatMedia(inputFolder, outputFolder string, filesPerGroup, numOutputs int) {
	mediaFiles, err := getMediaFiles(inputFolder)
	if err != nil {
		fmt.Println("Lỗi đọc thư mục:", err)
		return
	}

	if len(mediaFiles) < filesPerGroup {
		fmt.Println("❗ Không đủ file để ghép.")
		return
	}

	os.MkdirAll(outputFolder, os.ModePerm)
	rand.Seed(time.Now().Unix())
	timestamp := fmt.Sprintf("%d", time.Now().Unix())

	for i := 1; i <= numOutputs; i++ {
		// Random chọn n file
		rand.Shuffle(len(mediaFiles), func(i, j int) {
			mediaFiles[i], mediaFiles[j] = mediaFiles[j], mediaFiles[i]
		})
		selected := mediaFiles[:filesPerGroup]

		// Đếm số lượng mỗi định dạng
		extCount := make(map[string]int)
		hasVideo := false
		hasAudio := false
		for _, file := range selected {
			ext := strings.ToLower(filepath.Ext(file))
			extCount[ext]++
			if contains(videoExts, ext) {
				hasVideo = true
			}
			if contains(audioExts, ext) {
				hasAudio = true
			}
		}

		var ext string
		if len(extCount) == 1 {
			// Tất cả cùng định dạng
			for e := range extCount {
				ext = e
			}
		} else {
			// Nhiều loại → chọn loại phổ biến nhất
			maxCount := 0
			for e, count := range extCount {
				if count > maxCount {
					maxCount = count
					ext = e
				}
			}
			// Nếu có cả audio & video → ưu tiên mp4
			if hasVideo && hasAudio {
				ext = ".mp4"
			}
		}

		outputBase := fmt.Sprintf("%s_output_%d", timestamp, i)
		outputPath := filepath.Join(outputFolder, outputBase+ext)
		tracklistPath := filepath.Join(outputFolder, outputBase+"_tracklist.txt")
		tempListPath := filepath.Join(inputFolder, fmt.Sprintf("temp_list_%d.txt", i))

		// Ghi danh sách concat tạm
		err := createTempConcatList(selected, tempListPath)
		if err != nil {
			fmt.Println("❌ Không thể tạo danh sách file tạm:", err)
			continue
		}

		ffmpeg := utils.GetFFmpegPath()
		// Gọi ffmpeg
		cmd := exec.Command(ffmpeg, "-hide_banner", "-fflags", "+genpts",
			"-f", "concat", "-safe", "0", "-i", tempListPath,
			"-c", "copy", "-y", outputPath)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true} // Ẩn console trên Windows

		fmt.Println("🚀 Đang xử lý:", outputPath)
		err = cmd.Run()
		if err != nil {
			fmt.Println("❌ Lỗi khi ghép file:", err)
			continue
		}

		createTracklist(selected, tracklistPath)
		os.Remove(tempListPath)

		fmt.Println("Xong:", outputPath)
	}
	fmt.Println("🎉 Hoàn tất.")
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
	if len(os.Args) != 5 {
		fmt.Println("Usage: go run random_concat.go <input_folder> <output_folder> <files_per_group> <num_outputs>")
		return
	}

	inputFolder := os.Args[1]
	outputFolder := os.Args[2]
	filesPerGroup := atoi(os.Args[3])
	numOutputs := atoi(os.Args[4])

	if numOutputs <= 0 {
		fmt.Println("Lỗi: Output file count phải > 0")
		os.Exit(1)
	}
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

	concatMedia(inputFolder, outputFolder, filesPerGroup, numOutputs)
}

func atoi(s string) int {
	i, err := strconv.Atoi(s)
	if err != nil || i < 0 {
		fmt.Printf("Lỗi: %s phải là số nguyên >= 0\n", s)
		os.Exit(1)
	}
	return i
}
