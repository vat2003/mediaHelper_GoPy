// go_modules/convert.go
package main

import (
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

func main() {
	if len(os.Args) < 5 {
		fmt.Println("Thiếu tham số: input_folder output_folder input_ext output_ext")
		return
	}

	inputFolder := os.Args[1]
	outputFolder := os.Args[2]
	inputExt := strings.ToLower(os.Args[3])
	outputExt := strings.ToLower(os.Args[4])

	err := filepath.WalkDir(inputFolder, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}

		if !d.IsDir() && strings.HasSuffix(strings.ToLower(d.Name()), inputExt) {
			// Lấy tên file không kèm extension
			baseName := strings.TrimSuffix(d.Name(), filepath.Ext(d.Name()))
			outputPath := filepath.Join(outputFolder, baseName+outputExt)

			fmt.Printf("Convert: %s --> %s\n", path, outputPath)

			cmd := exec.Command("ffmpeg", "-y", "-i", path, "-c:v", "copy", "-c:a", "copy", outputPath)

			cmd.Stdout = os.Stdout
			cmd.Stderr = os.Stderr

			if err := cmd.Run(); err != nil {
				fmt.Println("Lỗi Convert: ", err)
			} else {
				fmt.Println("Successfully: ", outputPath)
			}
		}

		return nil
	})

	if err != nil {
		fmt.Println("Lỗi duyệt thư mục: ", err)
	}
}
