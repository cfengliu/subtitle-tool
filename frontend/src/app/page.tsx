"use client"

import type React from "react"

import { useState, useCallback, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Progress } from "@/components/ui/progress"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { toast } from "@/components/ui/sonner"
import { 
  Upload, 
  FileAudio, 
  Loader2, 
  CheckCircle, 
  AlertCircle, 
  FileText, 
  Subtitles, 
  Volume2, 
  Languages,
  X,
  Clock,
  Download,
  Copy,
  RefreshCw
} from "lucide-react"
import AudioCutter from "@/components/AudioCutter"

interface TranscriptionResult {
  srt?: string
  txt?: string
  detected_language?: string
  status?: string
  [key: string]: unknown
}

interface TaskStatus {
  task_id: string
  status: "running" | "completed" | "error" | "cancelled"
  progress: number
  filename?: string
  created_at?: string
  error_message?: string
}

interface ActiveTask {
  task_id: string
  filename: string
  language: string
  status: "running" | "completed" | "error" | "cancelled"
  progress: number
  created_at: string
}

interface ValidationError {
  loc: (string | number)[]
  msg: string
  type: string
}

interface HTTPValidationError {
  detail: ValidationError[]
}

export default function AudioTranscriptionPage() {
  const [file, setFile] = useState<File | null>(null)
  const [language, setLanguage] = useState<string>("auto")
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<TranscriptionResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [activeTab, setActiveTab] = useState<'txt' | 'srt'>('txt')
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  
  // 新增状态用于任务管理
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  const [taskProgress, setTaskProgress] = useState<number>(0)
  const [activeTasks, setActiveTasks] = useState<ActiveTask[]>([])

  // 標記是否為影片轉音檔後再轉錄的流程
  const [isVideoFlow, setIsVideoFlow] = useState<boolean>(false)

  // 常用語言列表
  const commonLanguages = [
    { code: "auto", name: "自動偵測" },
    { code: "zh", name: "中文" },
    { code: "en", name: "English" },
    { code: "ja", name: "日本語" },
    { code: "ko", name: "한국어" },
    { code: "es", name: "Español" },
    { code: "fr", name: "Français" },
    { code: "de", name: "Deutsch" },
    { code: "it", name: "Italiano" },
    { code: "pt", name: "Português" },
    { code: "ru", name: "Русский" },
    { code: "ar", name: "العربية" },
    { code: "hi", name: "हिन्दी" },
    { code: "th", name: "ไทย" },
    { code: "vi", name: "Tiếng Việt" },
    { code: "tr", name: "Türkçe" },
  ]

  // 獲取活躍任務列表
  const fetchActiveTasks = useCallback(async () => {
    try {
      const response = await fetch("/api/transcribe/tasks")
      if (response.ok) {
        const data = await response.json()
        setActiveTasks(data.active_tasks || [])
      }
    } catch (error) {
      console.error("Failed to fetch active tasks:", error)
    }
  }, [])

  // 輪詢任務狀態
  useEffect(() => {
    if (currentTaskId) {
      const pollStatus = async () => {
        try {
          const response = await fetch(`/api/transcribe/${currentTaskId}/status`)
          if (response.ok) {
            const status: TaskStatus = await response.json()
            const mappedProgress = isVideoFlow ? 50 + Math.round(status.progress / 2) : status.progress
            setTaskProgress(mappedProgress)
            
            if (status.status === "completed") {
              // 確保進度條結束於 100
              setTaskProgress(100)
              // 獲取結果
              const resultResponse = await fetch(`/api/transcribe/${currentTaskId}/result`)
              if (resultResponse.ok) {
                const resultData = await resultResponse.json()
                setResult(resultData)
                setIsLoading(false)
                setCurrentTaskId(null)
                fetchActiveTasks() // 刷新任務列表
                toast("轉錄完成", {
                  description: "音檔已成功轉錄，您可以查看結果並進行編輯。",
                })
                setIsVideoFlow(false)
              }
            } else if (status.status === "error" || status.status === "cancelled") {
              // 失敗或取消時重置 video flow 標記
              setIsVideoFlow(false)
              const errorMsg = status.error_message || `任務${status.status === "error" ? "失敗" : "已取消"}`
              setError(errorMsg)
              setIsLoading(false)
              setCurrentTaskId(null)
              fetchActiveTasks() // 刷新任務列表
              toast.error("轉錄失敗", {
                description: errorMsg,
              })
            }
          }
        } catch (error) {
          console.error("Failed to poll task status:", error)
        }
      }

      const interval = setInterval(pollStatus, 1000) // 每秒輪詢一次
      return () => clearInterval(interval)
    }
  }, [currentTaskId, fetchActiveTasks, isVideoFlow])

  // 定期刷新活躍任務列表
  useEffect(() => {
    fetchActiveTasks()
    const interval = setInterval(fetchActiveTasks, 5000) // 每5秒刷新一次
    return () => clearInterval(interval)
  }, [fetchActiveTasks])

  // 清理音檔URL以防止記憶體洩漏
  useEffect(() => {
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl)
      }
    }
  }, [audioUrl])

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
      const isAudio = droppedFile.type.startsWith("audio/")
      const isVideo = droppedFile.type.startsWith("video/")

      if (isAudio || isVideo) {
        // 清理之前的音檔URL
        if (audioUrl) {
          URL.revokeObjectURL(audioUrl)
        }

        setFile(droppedFile)
        setError(null)

        // 僅在音檔時產生預覽 URL，影片預覽將在後續支持
        if (isAudio) {
          const url = URL.createObjectURL(droppedFile)
          setAudioUrl(url)
        } else {
          setAudioUrl(null)
        }
      } else {
        setError("請選擇音檔或影片文件")
      }
    }
  }, [audioUrl])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      const isAudio = selectedFile.type.startsWith("audio/")
      const isVideo = selectedFile.type.startsWith("video/")

      if (isAudio || isVideo) {
        // 清理之前的音檔URL
        if (audioUrl) {
          URL.revokeObjectURL(audioUrl)
        }

        setFile(selectedFile)
        setError(null)

        if (isAudio) {
          const url = URL.createObjectURL(selectedFile)
          setAudioUrl(url)
        } else {
          setAudioUrl(null)
        }
      } else {
        setError("請選擇音檔或影片文件")
      }
    }
  }

  /* ---------------------------------------------
   *  Video -> Audio conversion before transcription
   * -------------------------------------------*/

  // Chunk upload size (5MB)
  const CHUNK_SIZE = 5 * 1024 * 1024

  /**
   * Upload video file in chunks to backend convert endpoint, returns task_id
   */
  const uploadFileInChunks = async (video: File): Promise<string> => {
    const totalChunks = Math.ceil(video.size / CHUNK_SIZE)
    let taskId: string | null = null

    for (let index = 0; index < totalChunks; index++) {
      const start = index * CHUNK_SIZE
      const end = Math.min(video.size, start + CHUNK_SIZE)
      const chunk = video.slice(start, end)

      const formData = new FormData()
      formData.append("chunk", chunk)
      formData.append("chunk_index", String(index))
      formData.append("total_chunks", String(totalChunks))
      formData.append("format", "mp3")
      formData.append("quality", "medium")
      formData.append("filename", video.name)
      if (taskId) {
        formData.append("task_id", taskId)
      }

      const response = await fetch("/api/convert-video/chunk-upload", {
        method: "POST",
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || "分片上傳失敗")
      }

      if (!taskId && data.task_id) {
        taskId = data.task_id as string
      }

      // 將 0~100 的 30% 分配給上傳進度
      setTaskProgress(Math.round(((index + 1) / totalChunks) * 30))
    }

    if (!taskId) throw new Error("task_id 不存在")

    return taskId
  }

  /**
   * 將影片檔轉換成音檔並下載，最終返回 File 物件
   */
  const convertVideoToAudio = async (video: File): Promise<File> => {
    // 1. 分片上傳
    const taskId = await uploadFileInChunks(video)

    // 2. 輪詢轉換進度
    let finished = false
    while (!finished) {
      const res = await fetch(`/api/convert-video/${taskId}/status`)
      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || "獲取轉換狀態失敗")
      }

      if (data.progress !== undefined) {
        // 映射到 30%~50%
        const mapped = 30 + Math.round((data.progress / 100) * 20)
        setTaskProgress(mapped)
      }

      if (data.status === "completed") {
        finished = true
      } else if (data.status === "failed" || data.status === "error") {
        throw new Error(data.error || "影片轉音檔失敗")
      } else {
        // wait 1 second
        await new Promise((r) => setTimeout(r, 1000))
      }
    }

    // 3. 下載音檔
    const audioRes = await fetch(`/api/convert-video/${taskId}/download`)
    if (!audioRes.ok) {
      throw new Error("下載音檔失敗")
    }

    const audioBlob = await audioRes.blob()

    // 解析 filename
    const contentDisposition = audioRes.headers.get("content-disposition")
    let filename = "converted_audio.mp3"
    if (contentDisposition) {
      const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      if (match) {
        filename = match[1].replace(/['"]/g, "")
      }
    }

    const audioFile = new File([audioBlob], filename, { type: audioBlob.type })

    // 建立預覽 URL
    const previewUrl = URL.createObjectURL(audioBlob)
    setAudioUrl(previewUrl)

    // 50% 基線
    setTaskProgress(50)

    return audioFile
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!file) {
      setError("請選擇文件")
      return
    }

    setIsLoading(true)
    setError(null)
    setResult(null)
    setTaskProgress(0)

    try {
      let targetFile: File = file

      // If the uploaded file is a video, convert it first
      if (file.type.startsWith("video/")) {
        toast("影片轉換中", {
          description: "正在將影片轉換為音檔，請稍候...",
        })
        targetFile = await convertVideoToAudio(file)
        // 更新為音檔文件以便後續預覽與操作
        setFile(targetFile)
      }

      const formData = new FormData()
      formData.append("file", targetFile)
      if (language && language !== "auto") {
        formData.append("language", language)
      }

      const response = await fetch("/api/transcribe", {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        if (response.status === 422) {
          const errorData: HTTPValidationError = await response.json()
          const errorMessages = errorData.detail.map((err) => err.msg).join(", ")
          throw new Error(`驗證錯誤: ${errorMessages}`)
        }
        throw new Error(`HTTP錯誤! 狀態: ${response.status}`)
      }

      const data = await response.json()
      if (data.task_id) {
        // 影片轉音檔後的進度基線 50%
        setCurrentTaskId(data.task_id)
        fetchActiveTasks()
        toast("轉錄已啟動", {
          description: "正在開始轉錄音檔...",
        })
        // 標記為影片流程
        if (file.type.startsWith("video/")) {
          setIsVideoFlow(true)
        }
      } else {
        // Old style immediate result
        setResult(data)
        setIsLoading(false)
        toast("轉錄完成", {
          description: "音檔已成功轉錄，您可以查看結果並進行編輯。",
        })
        setIsVideoFlow(false)
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "轉錄過程中發生錯誤"
      setError(errorMsg)
      setIsLoading(false)
      toast.error("轉錄失敗", {
        description: errorMsg,
      })
    }
  }

  const handleCancelTask = async (taskId: string) => {
    try {
      const response = await fetch(`/api/transcribe/${taskId}/cancel`, {
        method: "POST",
      })
      if (response.ok) {
        if (taskId === currentTaskId) {
          setCurrentTaskId(null)
          setIsLoading(false)
        }
        fetchActiveTasks() // 刷新任務列表
        toast("任務已取消", {
          description: "轉錄任務已成功取消。",
        })
      }
    } catch (error) {
      console.error("Failed to cancel task:", error)
    }
  }

  const resetForm = () => {
    setFile(null)
    setLanguage("auto")
    setResult(null)
    setError(null)
    setCurrentTaskId(null)
    setTaskProgress(0)
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl)
      setAudioUrl(null)
    }
    setIsVideoFlow(false)
  }

  const copyToClipboard = async (text: string) => {
    if (!text) {
      toast.error("內容為空", {
        description: "沒有可複製的文字。",
      })
      return
    }

    try {
      if (navigator.clipboard && window.isSecureContext) {
        // 現代瀏覽器，且在 HTTPS 或 localhost
        await navigator.clipboard.writeText(text)
      } else {
        // 後備方案：在非安全上下文或不支援 clipboard API 時使用
        const textarea = document.createElement("textarea")
        textarea.value = text
        textarea.style.position = "fixed"      // 避免跳動
        textarea.style.left = "-9999px"
        document.body.appendChild(textarea)
        textarea.focus()
        textarea.select()
        document.execCommand("copy")
        document.body.removeChild(textarea)
      }

      toast("已複製", {
        description: "內容已成功複製到剪貼板。",
      })
    } catch (error) {
      console.error("Copy failed:", error)
      toast.error("複製失敗", {
        description: "無法複製到剪貼板，請手動選擇並複製。",
      })
    }
  }

  const downloadFile = (text: string, format: 'txt' | 'srt') => {
    if (!text) {
      toast.error("內容為空", {
        description: "沒有可下載的內容。",
      })
      return
    }

    try {
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `transcription.${format}`
      a.style.display = 'none'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast("下載開始", {
        description: `${format.toUpperCase()} 文件已開始下載。`,
      })
    } catch (err) {
      console.error("Download error:", err)
      toast.error("下載失敗", {
        description: "無法下載文件，請稍後再試。",
      })
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "running":
        return <Badge variant="default" className="bg-blue-500"><Loader2 className="w-3 h-3 mr-1 animate-spin" />進行中</Badge>
      case "completed":
        return <Badge variant="default" className="bg-green-500"><CheckCircle className="w-3 h-3 mr-1" />已完成</Badge>
      case "error":
        return <Badge variant="destructive"><AlertCircle className="w-3 h-3 mr-1" />失敗</Badge>
      case "cancelled":
        return <Badge variant="secondary"><X className="w-3 h-3 mr-1" />已取消</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  return (
    <div className="container mx-auto py-8 px-4 max-w-7xl">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold mb-2">音檔 / 影片轉錄工具</h1>
        <p className="text-muted-foreground">上傳音檔或影片文件獲取準確的轉錄結果，支持實時進度監控</p>
      </div>

      <Tabs defaultValue="transcribe" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="transcribe">轉錄文件</TabsTrigger>
          <TabsTrigger value="tasks">任務管理</TabsTrigger>
        </TabsList>

        <TabsContent value="transcribe" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Upload Section */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Upload className="w-5 h-5" />
                  上傳音檔 / 影片文件
                </CardTitle>
                <CardDescription>選擇或拖拽音檔或影片文件進行轉錄</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <Label htmlFor="file-upload" className="cursor-pointer">
                      <div
                        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer hover:bg-muted/50 ${dragActive
                            ? "border-primary bg-primary/5"
                            : "border-muted-foreground/25 hover:border-muted-foreground/50"
                          }`}
                        onDragEnter={handleDrag}
                        onDragLeave={handleDrag}
                        onDragOver={handleDrag}
                        onDrop={handleDrop}
                      >
                        <FileAudio className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                        <div className="space-y-2">
                          <span className="text-sm font-medium">點擊上傳或拖拽文件</span>
                          <p className="text-xs text-muted-foreground">支持 MP3、WAV、M4A 等音檔格式</p>
                        </div>
                      </div>
                    </Label>
                    <Input id="file-upload" type="file" accept="audio/*,video/*" onChange={handleFileChange} className="hidden" />
                  </div>
                  
                  {/* Language Selection */}
                  <div className="space-y-2">
                    <Label htmlFor="language-select" className="flex items-center gap-2">
                      <Languages className="w-4 h-4" />
                      選擇語言
                    </Label>
                    <Select value={language} onValueChange={setLanguage}>
                      <SelectTrigger>
                        <SelectValue placeholder="選擇語言或自動檢測" />
                      </SelectTrigger>
                      <SelectContent>
                        {commonLanguages.map((lang) => (
                          <SelectItem key={lang.code} value={lang.code}>
                            {lang.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      選擇音檔的語言，或留空讓系統自動檢測
                    </p>
                  </div>

                  {file && (
                    <div className="space-y-3">
                      <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                        <FileAudio className="w-4 h-4" />
                        <span className="text-sm font-medium">{file.name}</span>
                        <span className="text-xs text-muted-foreground ml-auto">
                          {(file.size / 1024 / 1024).toFixed(2)} MB
                        </span>
                      </div>

                      {audioUrl && (
                        <div className="p-4 bg-muted rounded-lg">
                          <div className="flex items-center gap-2 mb-2">
                            <Volume2 className="w-4 h-4" />
                            <span className="text-sm font-medium">音檔預覽</span>
                          </div>
                          <div className="mt-4">
                            <AudioCutter
                              file={file}
                              onCut={(cutFile) => {
                                // 釋放舊 audioUrl
                                if (audioUrl) URL.revokeObjectURL(audioUrl)
                                setFile(cutFile)
                                setError(null)
                                const url = URL.createObjectURL(cutFile)
                                setAudioUrl(url)
                              }}
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
                    <Button type="submit" disabled={!file || isLoading} className="flex-1">
                      {isLoading ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          轉錄中...
                        </>
                      ) : (
                        <>
                          <Upload className="w-4 h-4 mr-2" />
                          開始轉錄
                        </>
                      )}
                    </Button>
                    {(file || result) && (
                      <Button type="button" onClick={resetForm} variant="outline">
                        重置
                      </Button>
                    )}
                    {currentTaskId && (
                      <Button 
                        type="button" 
                        onClick={() => handleCancelTask(currentTaskId)} 
                        variant="destructive"
                      >
                        <X className="w-4 h-4 mr-2" />
                        取消
                      </Button>
                    )}
                  </div>

                  {isLoading && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span>轉錄進度</span>
                        <span>{taskProgress}%</span>
                      </div>
                      <Progress value={taskProgress} className="w-full" />
                      <p className="text-sm text-center text-muted-foreground">正在處理您的音檔文件...</p>
                    </div>
                  )}
                </form>
              </CardContent>
            </Card>

            {/* Results Section */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="w-5 h-5" />
                  轉錄結果
                </CardTitle>
                <CardDescription>轉錄的文本將在這裡顯示</CardDescription>
              </CardHeader>
              <CardContent>
                {result ? (
                  <div className="space-y-4">
                    {/* Language Detection Result */}
                    {result.detected_language && (
                      <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                        <Languages className="w-4 h-4" />
                        <span className="text-sm font-medium">檢測語言:</span>
                        <span className="text-sm text-muted-foreground">
                          {commonLanguages.find(lang => lang.code === result.detected_language)?.name || 
                           result.detected_language}
                        </span>
                      </div>
                    )}

                    {audioUrl && (
                      <div className="p-4 bg-muted rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <Volume2 className="w-4 h-4" />
                          <span className="text-sm font-medium">原始音檔</span>
                        </div>
                        <audio
                          key={audioUrl}
                          controls
                          className="w-full"
                          preload="metadata"
                        >
                          <source src={audioUrl} type={file?.type} />
                          您的瀏覽器不支持音檔播放器。
                        </audio>
                      </div>
                    )}

                    {/* Format Tabs */}
                    <div className="flex space-x-1 bg-muted p-1 rounded-lg">
                      <button
                        onClick={() => setActiveTab('txt')}
                        className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors ${activeTab === 'txt'
                            ? 'bg-background text-foreground shadow-sm'
                            : 'text-muted-foreground hover:text-foreground'
                          }`}
                      >
                        <FileText className="w-4 h-4" />
                        純文本
                      </button>
                      <button
                        onClick={() => setActiveTab('srt')}
                        className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors ${activeTab === 'srt'
                            ? 'bg-background text-foreground shadow-sm'
                            : 'text-muted-foreground hover:text-foreground'
                          }`}
                      >
                        <Subtitles className="w-4 h-4" />
                        SRT字幕
                      </button>
                    </div>

                    {/* Content Display */}
                    <div className="p-4 bg-muted rounded-lg">
                      <Label className="text-sm font-medium mb-2 block">
                        {activeTab === 'txt' ? '轉錄文本：' : 'SRT字幕：'}
                      </Label>
                      <Textarea
                        value={activeTab === 'txt' ? result.txt || '' : result.srt || ''}
                        onChange={(e) => {
                          if (activeTab === 'txt') {
                            setResult(prev => prev ? { ...prev, txt: e.target.value } : null)
                          } else {
                            setResult(prev => prev ? { ...prev, srt: e.target.value } : null)
                          }
                        }}
                        className="min-h-[300px] resize-none font-mono text-sm"
                        placeholder={activeTab === 'txt' ? '轉錄文本將在這裡顯示...' : 'SRT字幕將在這裡顯示...'}
                      />
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-2">
                      <Button
                        onClick={() => {
                          const text = activeTab === 'txt' ? result.txt || '' : result.srt || ''
                          copyToClipboard(text)
                        }}
                        className="flex-1"
                      >
                        <Copy className="w-4 h-4 mr-2" />
                        複製到剪貼板
                      </Button>
                      <Button
                        onClick={() => {
                          const text = activeTab === 'txt' ? result.txt || '' : result.srt || ''
                          downloadFile(text, activeTab)
                        }}
                        variant="outline"
                        className="flex-1"
                      >
                        <Download className="w-4 h-4 mr-2" />
                        下載文件
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <FileAudio className="w-12 h-12 text-muted-foreground mb-4" />
                    <p className="text-muted-foreground">上傳音檔或影片文件以查看轉錄結果</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="tasks" className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Clock className="w-5 h-5" />
                    活躍任務
                  </CardTitle>
                  <CardDescription>管理正在進行的轉錄任務</CardDescription>
                </div>
                <Button onClick={fetchActiveTasks} variant="outline" size="sm">
                  <RefreshCw className="w-4 h-4 mr-2" />
                  刷新
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {activeTasks.length > 0 ? (
                <div className="space-y-4">
                  {activeTasks.map((task) => (
                    <div key={task.task_id} className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <FileAudio className="w-4 h-4" />
                          <span className="font-medium">{task.filename}</span>
                          {getStatusBadge(task.status)}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-muted-foreground">
                            {new Date(task.created_at).toLocaleString()}
                          </span>
                          {task.status === "running" && (
                            <Button
                              onClick={() => handleCancelTask(task.task_id)}
                              variant="outline"
                              size="sm"
                            >
                              <X className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </div>
                      
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                          <span>語言: {task.language === "auto" ? "自動檢測" : task.language}</span>
                          <span>進度: {task.progress}%</span>
                        </div>
                        {task.status === "running" && (
                          <Progress value={task.progress} className="w-full" />
                        )}
                      </div>
                      
                      <div className="mt-2 text-xs text-muted-foreground">
                        任務ID: {task.task_id}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Clock className="w-12 h-12 text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">當前沒有活躍的轉錄任務</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
