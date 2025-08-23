package main

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"syscall"

	"github.com/vat2003/mediaHelper_GoPy/go_modules/utils"
)

func main() {
	if len(os.Args) < 5 {
		fmt.Println("Usage: videoScale <input_video> <output_file> <resolution> <cpu|gpu> [video_bitrate] [fps] [audio_bitrate] [preset]")
		os.Exit(1)
	}

	inputVideo := os.Args[1]
	outputFile := os.Args[2]
	resolution := os.Args[3]                 // e.g. 3840x2160 or 1920x1080
	processor := strings.ToLower(os.Args[4]) // cpu or gpu

	videoBitrate := "3000k"
	if len(os.Args) >= 6 && os.Args[5] != "" {
		videoBitrate = os.Args[5]
	}

	fps := 0
	if len(os.Args) >= 7 && os.Args[6] != "" {
		var err error
		fps, err = strconv.Atoi(os.Args[6])
		if err != nil || fps < 0 {
			log.Fatalf("❌ FPS không hợp lệ: %s", os.Args[6])
		}
	}

	audioBitrate := "128k"
	if len(os.Args) >= 8 && os.Args[7] != "" {
		audioBitrate = os.Args[7]
	}

	preset := "medium" // CPU x264 preset; will be mapped for NVENC if GPU
	if len(os.Args) >= 9 && os.Args[8] != "" {
		preset = os.Args[8]
	}

	ffmpeg := resolveToolPath(utils.GetFFmpegPath(), "ffmpeg")

	// Build args depending on CPU/GPU
	var args []string
	if processor == "gpu" {
		args = buildArgsGPU(inputVideo, outputFile, resolution, videoBitrate, fps, audioBitrate, mapPresetNVENC(preset))
	} else {
		args = buildArgsCPU(inputVideo, outputFile, resolution, videoBitrate, fps, audioBitrate, preset)
	}

	// Try run; if GPU path fails (e.g., scale_cuda not present / NVDEC mismatch),
	// gracefully fallback to CPU filters + NVENC encode (still GPU encode).
	if err := runFFmpeg(ffmpeg, args); err != nil {
		if processor == "gpu" {
			fmt.Println("⚠️ GPU filter path lỗi, fallback sang filter CPU nhưng vẫn NVENC encode…")
			fallback := buildArgsCPUWithNVENC(inputVideo, outputFile, resolution, videoBitrate, fps, audioBitrate, mapPresetNVENC(preset))
			if err2 := runFFmpeg(ffmpeg, fallback); err2 != nil {
				log.Fatalf("❌ FFmpeg failed (fallback): %v", err2)
			}
		} else {
			log.Fatalf("❌ FFmpeg failed: %v", err)
		}
	}

	fmt.Println("✅ Video đã được scale thành công:", outputFile)
}

func buildArgsCPU(in, out, res, vbr string, fps int, abr, preset string) []string {
	vf := []string{}
	if fps > 0 {
		vf = append(vf, fmt.Sprintf("fps=%d", fps))
	}
	vf = append(vf, fmt.Sprintf("scale=%s", res))
	vf = append(vf, "format=yuv420p")
	filter := strings.Join(vf, ",")

	args := []string{"-y", "-i", in, "-vf", filter,
		"-c:v", "libx264", "-preset", preset, "-b:v", vbr,
		"-c:a", "aac", "-b:a", abr,
		"-pix_fmt", "yuv420p",
	}
	if strings.EqualFold(filepath.Ext(out), ".mp4") {
		args = append(args, "-movflags", "+faststart")
	}
	args = append(args, out)
	return args
}

func buildArgsGPU(in, out, res, vbr string, fps int, abr, nvPreset string) []string {
	// Keep decode on CPU (more robust), upload to GPU, then scale on GPU, then NVENC encode
	// If you *know* NVDEC supports your source, you can add: -hwaccel cuda -hwaccel_output_format cuda before -i
	vfParts := []string{}
	if fps > 0 {
		// fps is a software filter; apply before uploading to GPU
		vfParts = append(vfParts, fmt.Sprintf("fps=%d", fps))
	}
	vfParts = append(vfParts, "hwupload_cuda")
	vfParts = append(vfParts, fmt.Sprintf("scale_cuda=%s:format=yuv420p", res))
	filter := strings.Join(vfParts, ",")

	args := []string{"-y", "-i", in, "-vf", filter,
		"-c:v", "h264_nvenc", "-preset", nvPreset, "-b:v", vbr,
		"-c:a", "aac", "-b:a", abr,
		// Do NOT set -pix_fmt outside CUDA filter; handled by scale_cuda
	}
	if strings.EqualFold(filepath.Ext(out), ".mp4") {
		args = append(args, "-movflags", "+faststart")
	}
	args = append(args, out)
	return args
}

func buildArgsCPUWithNVENC(in, out, res, vbr string, fps int, abr, nvPreset string) []string {
	// CPU filters, NVENC encode
	vf := []string{}
	if fps > 0 {
		vf = append(vf, fmt.Sprintf("fps=%d", fps))
	}
	vf = append(vf, fmt.Sprintf("scale=%s", res))
	vf = append(vf, "format=yuv420p")
	filter := strings.Join(vf, ",")

	args := []string{"-y", "-i", in, "-vf", filter,
		"-c:v", "h264_nvenc", "-preset", nvPreset, "-b:v", vbr,
		"-c:a", "aac", "-b:a", abr,
	}
	if strings.EqualFold(filepath.Ext(out), ".mp4") {
		args = append(args, "-movflags", "+faststart")
	}
	args = append(args, out)
	return args
}

func runFFmpeg(ffmpeg string, args []string) error {
	cmd := exec.Command(ffmpeg, args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
	fmt.Println("🚀 Đang scale video…")
	fmt.Println("FFmpeg:", ffmpeg)
	fmt.Println("Args:", strings.Join(args, " "))
	return cmd.Run()
}

func mapPresetNVENC(p string) string {
	s := strings.ToLower(strings.TrimSpace(p))
	switch s {
	case "p1", "p2", "p3", "p4", "p5", "p6", "p7":
		return s
	case "ultrafast":
		return "p1"
	case "superfast":
		return "p2"
	case "veryfast":
		return "p3"
	case "faster":
		return "p4"
	case "fast":
		return "p4"
	case "medium", "default":
		return "p5"
	case "slow":
		return "p6"
	case "veryslow":
		return "p7"
	default:
		return "p5"
	}
}

// resolveToolPath: try absolute, add .exe on Windows, or look on PATH
func resolveToolPath(candidate, fallback string) string {
	c := strings.TrimSpace(candidate)
	if c != "" {
		if filepath.IsAbs(c) {
			if fi, err := os.Stat(c); err == nil && !fi.IsDir() {
				return c
			}
		} else {
			// relative to CWD
			cand := filepath.Clean(c)
			if fi, err := os.Stat(cand); err == nil && !fi.IsDir() {
				return cand
			}
		}
		if runtime.GOOS == "windows" && !strings.HasSuffix(strings.ToLower(c), ".exe") {
			cand := c + ".exe"
			if fi, err := os.Stat(cand); err == nil && !fi.IsDir() {
				return cand
			}
		}
	}
	if lp, err := exec.LookPath(c); err == nil {
		return lp
	}
	if lp, err := exec.LookPath(fallback); err == nil {
		return lp
	}
	log.Fatalf("❌ Không tìm thấy %s (candidate: %q)", fallback, candidate)
	return ""
}
