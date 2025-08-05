package utils

import (
	"fmt"
	"os"
	"path/filepath"
)

// Lấy đường dẫn đến thư mục "assets/ffmpeg" (ở thư mục gốc dự án)
func getFFmpegBinDir() string {
	execPath, err := os.Executable()
	if err != nil {
		fmt.Println("❌ Không lấy được đường dẫn thực thi:", err)
		os.Exit(1)
	}

	// Truy ngược lên thư mục gốc dự án (C:\GoProjects)
	// Ví dụ: nếu execPath = C:\GoProjects\go_modules\loop\your_app.exe
	// thì rootDir = C:\GoProjects
	moduleDir := filepath.Dir(execPath)
	goModulesDir := filepath.Dir(moduleDir)
	projectRoot := filepath.Dir(goModulesDir)

	return filepath.Join(projectRoot, "assets", "ffmpeg")
}

// Trả về đường dẫn đến ffmpeg.exe
func GetFFmpegPath() string {
	return filepath.Join(getFFmpegBinDir(), "ffmpeg.exe")
}

// Trả về đường dẫn đến ffprobe.exe
func GetFFprobePath() string {
	return filepath.Join(getFFmpegBinDir(), "ffprobe.exe")
}
