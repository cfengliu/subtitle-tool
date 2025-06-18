"use client"

import type React from "react"
import { useState, useCallback, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Progress } from "@/components/ui/progress"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "sonner"
import { 
  Upload, 
  FileVideo, 
  FileAudio,
  FileText,
  Loader2, 
  CheckCircle, 
  AlertCircle, 
  Download,
  Volume2,
  Settings
} from "lucide-react"

interface VideoToAudioProps {
  onAudioGenerated?: (audioFile: File) => void
}

export default function VideoToAudio({ onAudioGenerated }: VideoToAudioProps) {
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [isConverting, setIsConverting] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [audioFormat, setAudioFormat] = useState<'mp3' | 'wav' | 'ogg'>('mp3')
  const [audioQuality, setAudioQuality] = useState<'high' | 'medium' | 'low'>('medium')
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  
  const videoRef = useRef<HTMLVideoElement>(null)
  const audioRef = useRef<HTMLAudioElement>(null)

  // 格式選項
  const formatOptions = [
    { value: 'mp3', label: 'MP3', description: '通用格式，檔案較小' },
    { value: 'wav', label: 'WAV', description: '無損格式，檔案較大' },
    { value: 'ogg', label: 'OGG', description: '開源格式，品質良好' }
  ]

  const qualityOptions = [
    { value: 'high', label: '高品質', bitrate: '320kbps' },
    { value: 'medium', label: '中品質', bitrate: '192kbps' },
    { value: 'low', label: '低品質', bitrate: '128kbps' }
  ]

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0]
      if (droppedFile.type.startsWith("video/")) {
        handleVideoFile(droppedFile)
      } else {
        setError("請選擇影片文件")
      }
    }
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      if (selectedFile.type.startsWith("video/")) {
        handleVideoFile(selectedFile)
      } else {
        setError("請選擇影片文件")
      }
    }
  }

  const handleVideoFile = (file: File) => {
    // 清理之前的 URL
    if (videoUrl) URL.revokeObjectURL(videoUrl)
    if (audioUrl) URL.revokeObjectURL(audioUrl)
    
    setVideoFile(file)
    setAudioFile(null)
    setError(null)
    setProgress(0)
    
    const url = URL.createObjectURL(file)
    setVideoUrl(url)
    setAudioUrl(null)
  }

  const convertVideoToAudio = async () => {
    if (!videoFile) {
      setError("請選擇影片文件")
      return
    }

    setIsConverting(true)
    setError(null)
    setProgress(0)

    try {
      // 創建 video 元素來獲取音頻
      const video = document.createElement('video')
      video.src = URL.createObjectURL(videoFile)
      
      await new Promise((resolve, reject) => {
        video.onloadedmetadata = resolve
        video.onerror = reject
      })

      // 創建 AudioContext 和相關節點
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
      const source = audioContext.createMediaElementSource(video)
      const destination = audioContext.createMediaStreamDestination()
      source.connect(destination)

      // 檢查瀏覽器支持的格式
      const getSupportedMimeType = (): string => {
        const types = [
          'audio/webm;codecs=opus',
          'audio/webm',
          'audio/ogg;codecs=opus',
          'audio/ogg',
          'audio/wav',
          'audio/mpeg'
        ]
        
        for (const type of types) {
          if (MediaRecorder.isTypeSupported(type)) {
            return type
          }
        }
        
        // 如果沒有找到支持的格式，使用默認格式
        return 'audio/webm'
      }

      const supportedMimeType = getSupportedMimeType()
      console.log('Using MIME type:', supportedMimeType)

      // 創建 MediaRecorder 來錄製音頻
      const mediaRecorder = new MediaRecorder(destination.stream, {
        mimeType: supportedMimeType
      })

      const chunks: Blob[] = []
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(chunks, { type: supportedMimeType })
        
        // 如果用戶選擇的格式與錄製格式不同，需要轉換
        // 由於瀏覽器限制，我們先創建原始格式的文件
        const originalExtension = getExtensionFromMimeType(supportedMimeType)
        const convertedAudioFile = new File([audioBlob], `converted.${originalExtension}`, {
          type: supportedMimeType
        })
        
        setAudioFile(convertedAudioFile)
        const audioURL = URL.createObjectURL(convertedAudioFile)
        setAudioUrl(audioURL)
        setIsConverting(false)
        setProgress(100)
        
        // 調用回調函數
        if (onAudioGenerated) {
          onAudioGenerated(convertedAudioFile)
        }
        
        toast("轉換完成", {
          description: `影片已成功轉換為 ${originalExtension.toUpperCase()} 音頻文件。`,
        })
      }

      // 開始錄製
      mediaRecorder.start()
      video.play()

      // 監聽播放進度
      const updateProgress = () => {
        if (video.duration > 0) {
          const progressPercent = (video.currentTime / video.duration) * 100
          setProgress(progressPercent)
        }
      }

      video.ontimeupdate = updateProgress

      // 當影片播放完成時停止錄製
      video.onended = () => {
        mediaRecorder.stop()
        audioContext.close()
        URL.revokeObjectURL(video.src)
      }

    } catch (err) {
      console.error("Conversion error:", err)
      setError("轉換過程中發生錯誤：" + (err instanceof Error ? err.message : "未知錯誤"))
      setIsConverting(false)
      toast.error("轉換失敗", {
        description: "無法轉換影片，請檢查文件格式或稍後再試。",
      })
    }
  }

  const getMimeType = (format: string): string => {
    switch (format) {
      case 'mp3': return 'audio/mpeg'
      case 'wav': return 'audio/wav'
      case 'ogg': return 'audio/ogg'
      default: return 'audio/mpeg'
    }
  }

  const getExtensionFromMimeType = (mimeType: string): string => {
    if (mimeType.includes('webm')) return 'webm'
    if (mimeType.includes('ogg')) return 'ogg'
    if (mimeType.includes('wav')) return 'wav'
    if (mimeType.includes('mpeg')) return 'mp3'
    return 'webm'
  }

  const downloadAudio = () => {
    if (!audioFile || !audioUrl) {
      toast.error("沒有可下載的音頻文件")
      return
    }

    try {
      const a = document.createElement('a')
      a.href = audioUrl
      // 使用實際的文件名
      a.download = audioFile.name
      a.style.display = 'none'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      
      toast("下載開始", {
        description: `音頻文件已開始下載。`,
      })
    } catch (err) {
      console.error("Download error:", err)
      toast.error("下載失敗", {
        description: "無法下載文件，請稍後再試。",
      })
    }
  }

  const toggleVideoPlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause()
      } else {
        videoRef.current.play()
      }
      setIsPlaying(!isPlaying)
    }
  }

  const resetForm = () => {
    setVideoFile(null)
    setAudioFile(null)
    setError(null)
    setProgress(0)
    setIsPlaying(false)
    
    if (videoUrl) {
      URL.revokeObjectURL(videoUrl)
      setVideoUrl(null)
    }
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl)
      setAudioUrl(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Upload Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="w-5 h-5" />
              上傳影片文件
            </CardTitle>
            <CardDescription>選擇或拖拽影片文件進行音頻轉換</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="video-upload" className="cursor-pointer">
                <div
                  className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer hover:bg-muted/50 ${
                    dragActive
                      ? "border-primary bg-primary/5"
                      : "border-muted-foreground/25 hover:border-muted-foreground/50"
                  }`}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                >
                  <FileVideo className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                  <div className="space-y-2">
                    <span className="text-sm font-medium">點擊上傳或拖拽影片</span>
                    <p className="text-xs text-muted-foreground">支持 MP4、AVI、MOV 等影片格式</p>
                  </div>
                </div>
              </Label>
              <Input 
                id="video-upload" 
                type="file" 
                accept="video/*" 
                onChange={handleFileChange} 
                className="hidden" 
              />
            </div>

            {/* Settings */}
            <div className="space-y-4 p-4 bg-muted rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Settings className="w-4 h-4" />
                <span className="text-sm font-medium">轉換設定</span>
              </div>
              
              <div className="space-y-4">
                <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                  <p className="text-sm text-yellow-800 dark:text-yellow-200">
                    <strong>注意：</strong>由於瀏覽器限制，實際輸出格式將根據您的瀏覽器支持情況自動選擇（通常為 WebM 或 OGG 格式）。
                  </p>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="format-select">偏好格式</Label>
                    <Select value={audioFormat} onValueChange={(value: 'mp3' | 'wav' | 'ogg') => setAudioFormat(value)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {formatOptions.map((format) => (
                          <SelectItem key={format.value} value={format.value}>
                            <div>
                              <div className="font-medium">{format.label}</div>
                              <div className="text-xs text-muted-foreground">{format.description}</div>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="quality-select">音頻品質</Label>
                    <Select value={audioQuality} onValueChange={(value: 'high' | 'medium' | 'low') => setAudioQuality(value)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {qualityOptions.map((quality) => (
                          <SelectItem key={quality.value} value={quality.value}>
                            <div>
                              <div className="font-medium">{quality.label}</div>
                              <div className="text-xs text-muted-foreground">{quality.bitrate}</div>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            </div>

            {videoFile && (
              <div className="space-y-3">
                <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                  <FileVideo className="w-4 h-4" />
                  <span className="text-sm font-medium">{videoFile.name}</span>
                  <span className="text-xs text-muted-foreground ml-auto">
                    {(videoFile.size / 1024 / 1024).toFixed(2)} MB
                  </span>
                </div>

                {videoUrl && (
                  <div className="p-4 bg-muted rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Volume2 className="w-4 h-4" />
                      <span className="text-sm font-medium">影片預覽</span>
                    </div>
                    <div className="relative">
                      <video
                        ref={videoRef}
                        src={videoUrl}
                        className="w-full max-h-48 rounded-lg"
                        controls
                        preload="metadata"
                        onPlay={() => setIsPlaying(true)}
                        onPause={() => setIsPlaying(false)}
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="flex gap-2">
              <Button 
                onClick={convertVideoToAudio} 
                disabled={!videoFile || isConverting} 
                className="flex-1"
              >
                {isConverting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    轉換中...
                  </>
                ) : (
                  <>
                    <FileAudio className="w-4 h-4 mr-2" />
                    開始轉換
                  </>
                )}
              </Button>
              {videoFile && (
                <Button onClick={resetForm} variant="outline">
                  重置
                </Button>
              )}
            </div>

            {isConverting && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>轉換進度</span>
                  <span>{Math.round(progress)}%</span>
                </div>
                <Progress value={progress} className="w-full" />
                <p className="text-sm text-center text-muted-foreground">正在提取音頻...</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Results Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5" />
              轉換結果
            </CardTitle>
            <CardDescription>轉換後的音頻文件將在這裡顯示</CardDescription>
          </CardHeader>
          <CardContent>
            {audioFile && audioUrl ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                  <FileAudio className="w-4 h-4" />
                  <span className="text-sm font-medium">{audioFile.name}</span>
                  <span className="text-xs text-muted-foreground ml-auto">
                    {(audioFile.size / 1024 / 1024).toFixed(2)} MB
                  </span>
                </div>

                <div className="p-4 bg-muted rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Volume2 className="w-4 h-4" />
                    <span className="text-sm font-medium">音頻預覽</span>
                  </div>
                  <audio
                    ref={audioRef}
                    controls
                    className="w-full"
                    preload="metadata"
                  >
                    <source src={audioUrl} type={audioFile.type} />
                    您的瀏覽器不支持音頻播放器。
                  </audio>
                </div>

                <div className="flex gap-2">
                  <Button onClick={downloadAudio} className="flex-1">
                    <Download className="w-4 h-4 mr-2" />
                    下載音頻文件
                  </Button>
                  <Button 
                    onClick={() => window.open('/?audio=' + encodeURIComponent(audioFile.name), '_blank')} 
                    variant="outline"
                    className="flex-1"
                  >
                    <FileText className="w-4 h-4 mr-2" />
                    轉錄音頻
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <FileAudio className="w-12 h-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">上傳影片文件以查看轉換結果</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
} 