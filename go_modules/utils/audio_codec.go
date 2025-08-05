package utils

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os/exec"
	"strings"
)

// GetAudioCodec dùng ffprobe để lấy codec audio từ video
func GetAudioCodec(inputFile string, ffprobePath string) (string, error) {
	cmd := exec.Command(ffprobePath,
		"-v", "error",
		"-select_streams", "a:0",
		"-show_entries", "stream=codec_name",
		"-of", "json",
		inputFile,
	)

	var out bytes.Buffer
	cmd.Stdout = &out
	err := cmd.Run()
	if err != nil {
		return "", err
	}

	// Parse JSON từ ffprobe
	type FFProbeOutput struct {
		Streams []struct {
			CodecName string `json:"codec_name"`
		} `json:"streams"`
	}

	var result FFProbeOutput
	err = json.Unmarshal(out.Bytes(), &result)
	if err != nil || len(result.Streams) == 0 {
		return "", fmt.Errorf("không thể phân tích ffprobe")
	}

	return result.Streams[0].CodecName, nil
}

// ShouldCopyCodec kiểm tra xem có thể dùng -c:a copy với outputExt không
func ShouldCopyCodec(codec string, outputExt string) bool {
	outputExt = strings.ToLower(outputExt)

	switch outputExt {
	case ".mp3":
		return codec == "mp3"
	case ".aac":
		return codec == "aac"
	case ".m4a":
		return codec == "aac" || codec == "alac"
	case ".wav":
		return strings.HasPrefix(codec, "pcm")
	case ".flac":
		return codec == "flac"
	case ".opus":
		return codec == "opus"
	default:
		return false
	}
}

// GetTranscodeCodec trả về codec phù hợp với đuôi file output
func GetTranscodeCodec(outputExt string) string {
	switch strings.ToLower(outputExt) {
	case ".mp3":
		return "libmp3lame"
	case ".aac", ".m4a":
		return "aac"
	case ".wav":
		return "pcm_s16le"
	case ".flac":
		return "flac"
	case ".opus":
		return "libopus"
	default:
		return "aac" // fallback
	}
}
