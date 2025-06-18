"use client"

import type React from "react"
import { useState, useCallback, useRef, useEffect } from "react"
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
  Settings,
  X
} from "lucide-react"

interface VideoToAudioProps {
  onAudioGenerated?: (audioFile: File) => void
}

interface ConversionTask {
  task_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
  progress?: number
  error?: string
  result_url?: string
  filename?: string
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
  const [currentTask, setCurrentTask] = useState<ConversionTask | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  
  const videoRef = useRef<HTMLVideoElement>(null)
  const audioRef = useRef<HTMLAudioElement>(null)
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)

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

  // 清理函數
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
      if (videoUrl) {
        URL.revokeObjectURL(videoUrl)
      }
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl)
      }
    }
  }, [videoUrl, audioUrl])

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }, [])

  const handleVideoFile = useCallback((file: File) => {
    // 清理之前的 URL
    if (videoUrl) URL.revokeObjectURL(videoUrl)
    if (audioUrl) URL.revokeObjectURL(audioUrl)
    
    setVideoFile(file)
    setAudioFile(null)
    setError(null)
    setProgress(0)
    setCurrentTask(null)
    
    const url = URL.createObjectURL(file)
    setVideoUrl(url)
    setAudioUrl(null)
  }, [videoUrl, audioUrl])

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
  }, [handleVideoFile])

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

  // 輪詢任務狀態
  const pollTaskStatus = async (taskId: string) => {
    try {
      const response = await fetch(`/api/convert-video/${taskId}/status`)
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.detail || '獲取任務狀態失敗')
      }
      
      setCurrentTask(data)
      
      if (data.progress !== undefined) {
        setProgress(data.progress)
      }
      
      if (data.status === 'completed') {
        // 任務完成，停止輪詢
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = null
        }
        
        // 下載結果
        await downloadResult(taskId)
        setIsConverting(false)
        
        toast("轉換完成", {
          description: `影片已成功轉換為 ${audioFormat.toUpperCase()} 音頻文件。`,
        })
      } else if (data.status === 'failed') {
        // 任務失敗
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = null
        }
        
        setError(data.error || '轉換失敗')
        setIsConverting(false)
        
        toast.error("轉換失敗", {
          description: data.error || "轉換過程中發生錯誤",
        })
      } else if (data.status === 'cancelled') {
        // 任務取消
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = null
        }
        
        setIsConverting(false)
        setProgress(0)
        
        toast("任務已取消", {
          description: "轉換任務已被取消",
        })
      }
    } catch (err) {
      console.error("Poll task status error:", err)
      setError(err instanceof Error ? err.message : '獲取任務狀態失敗')
    }
  }

  // 下載轉換結果
  const downloadResult = async (taskId: string) => {
    try {
      const response = await fetch(`/api/convert-video/${taskId}/result`)
      
      if (!response.ok) {
        throw new Error('下載結果失敗')
      }
      
      const audioBlob = await response.blob()
      const contentDisposition = response.headers.get('content-disposition')
      let filename = 'converted_audio.mp3'
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
        if (filenameMatch) {
          filename = filenameMatch[1].replace(/['"]/g, '')
        }
      }
      
      const audioFile = new File([audioBlob], filename, { type: audioBlob.type })
      setAudioFile(audioFile)
      
      const audioURL = URL.createObjectURL(audioBlob)
      setAudioUrl(audioURL)
      
      // 調用回調函數
      if (onAudioGenerated) {
        onAudioGenerated(audioFile)
      }
      
    } catch (err) {
      console.error("Download result error:", err)
      setError(err instanceof Error ? err.message : '下載結果失敗')
    }
  }

  // 開始轉換
  const convertVideoToAudio = async () => {
    if (!videoFile) {
      setError("請選擇影片文件")
      return
    }

    setIsConverting(true)
    setIsUploading(true)
    setError(null)
    setProgress(0)
    setCurrentTask(null)

    try {
      // 創建 FormData
      const formData = new FormData()
      formData.append('file', videoFile)
      formData.append('format', audioFormat)
      formData.append('quality', audioQuality)

      // 上傳文件並開始轉換
      const response = await fetch('/api/convert-video', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.detail || '上傳失敗')
      }
      
      setIsUploading(false)
      setCurrentTask(data)
      
      toast("上傳成功", {
        description: "文件已上傳，開始轉換...",
      })
      
      // 開始輪詢任務狀態
      pollIntervalRef.current = setInterval(() => {
        pollTaskStatus(data.task_id)
      }, 1000) // 每秒輪詢一次
      
    } catch (err) {
      console.error("Conversion error:", err)
      setError(err instanceof Error ? err.message : '轉換失敗')
      setIsConverting(false)
      setIsUploading(false)
      
      toast.error("轉換失敗", {
        description: err instanceof Error ? err.message : "轉換過程中發生錯誤",
      })
    }
  }

  // 取消轉換
  const cancelConversion = async () => {
    if (!currentTask) return
    
    try {
      const response = await fetch(`/api/convert-video/${currentTask.task_id}/cancel`, {
        method: 'POST',
      })
      
      if (response.ok) {
        toast("取消成功", {
          description: "轉換任務已取消",
        })
      }
    } catch (err) {
      console.error("Cancel conversion error:", err)
      toast.error("取消失敗", {
        description: "無法取消轉換任務",
      })
    }
  }

  const downloadAudio = () => {
    if (!audioFile || !audioUrl) {
      toast.error("沒有可下載的音頻文件")
      return
    }

    try {
      const a = document.createElement('a')
      a.href = audioUrl
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

  const resetForm = () => {
    // 清理輪詢
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
    
    setVideoFile(null)
    setAudioFile(null)
    setError(null)
    setProgress(0)
    setIsConverting(false)
    setIsUploading(false)
    setCurrentTask(null)
    
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
                disabled={isConverting}
              />
            </div>

            {/* Settings */}
            <div className="space-y-4 p-4 bg-muted rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Settings className="w-4 h-4" />
                <span className="text-sm font-medium">轉換設定</span>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="format-select">輸出格式</Label>
                  <Select 
                    value={audioFormat} 
                    onValueChange={(value: 'mp3' | 'wav' | 'ogg') => setAudioFormat(value)}
                    disabled={isConverting}
                  >
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
                  <Select 
                    value={audioQuality} 
                    onValueChange={(value: 'high' | 'medium' | 'low') => setAudioQuality(value)}
                    disabled={isConverting}
                  >
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
                {isUploading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    上傳中...
                  </>
                ) : isConverting ? (
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
              
              {isConverting && currentTask && (
                <Button onClick={cancelConversion} variant="outline" size="icon">
                  <X className="w-4 h-4" />
                </Button>
              )}
              
              {videoFile && !isConverting && (
                <Button onClick={resetForm} variant="outline">
                  重置
                </Button>
              )}
            </div>

            {isConverting && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>
                    {isUploading ? '上傳進度' : '轉換進度'}
                  </span>
                  <span>{Math.round(progress)}%</span>
                </div>
                <Progress value={progress} className="w-full" />
                <p className="text-sm text-center text-muted-foreground">
                  {isUploading ? '正在上傳文件...' : 
                   currentTask?.status === 'pending' ? '等待處理...' : 
                   currentTask?.status === 'processing' ? '正在轉換...' : 
                   '處理中...'}
                </p>
                {currentTask && (
                  <p className="text-xs text-center text-muted-foreground">
                    任務 ID: {currentTask.task_id}
                  </p>
                )}
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