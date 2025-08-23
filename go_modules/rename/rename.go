package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// Xử lý tên file: removeChars
func processName(name, removeChars string) string {
	if removeChars != "" {
		name = strings.ReplaceAll(name, removeChars, "")
	}
	return name
}

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Thiếu tham số: input_file [prefix] [suffix] [remove_chars]")
		fmt.Println("Ví dụ: rename input.mp4 pre suf -")
		os.Exit(1)
	}

	inputFile := os.Args[1]

	// Tuỳ chọn
	prefix := ""
	if len(os.Args) >= 3 {
		prefix = os.Args[2]
	}

	suffix := ""
	if len(os.Args) >= 4 {
		suffix = os.Args[3]
	}

	removeChars := ""
	if len(os.Args) >= 5 {
		removeChars = os.Args[4]
	}

	// Lấy tên file gốc
	filename := filepath.Base(inputFile)
	ext := filepath.Ext(filename)
	nameWithoutExt := strings.TrimSuffix(filename, ext)

	// Xử lý remove
	nameWithoutExt = processName(nameWithoutExt, removeChars)

	// Ghép prefix + suffix
	newName := fmt.Sprintf("%s%s%s%s", prefix, nameWithoutExt, suffix, ext)
	newFilePath := filepath.Join(filepath.Dir(inputFile), newName)

	fmt.Printf("🔄 Đổi tên: %s --> %s\n", inputFile, newName)

	err := os.Rename(inputFile, newFilePath)
	if err != nil {
		fmt.Println("❌ Lỗi đổi tên:", err)
		os.Exit(2)
	}

	fmt.Println("✅ Đổi tên thành công:", newName)
}
