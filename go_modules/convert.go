// go_modules/convert.go
package main

import (
	"fmt"
	"os"
	"os/exec"
)

func main() {
	if len(os.Args) < 3 {
		fmt.Println("❌ Thiếu tham số: input output")
		return
	}
	input := os.Args[1]
	output := os.Args[2]

	cmd := exec.Command("ffmpeg", "-y", "-i", input,
		"-c:v", "copy",
		"-c:a", "copy",
		output)

	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	err := cmd.Run()
	if err != nil {
		fmt.Println("❌ Lỗi khi convert:", err)
		return
	}
	fmt.Println("✅ Convert thành công!")
}
