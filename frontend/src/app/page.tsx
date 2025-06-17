"use client"

import type React from "react"

import { useState, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Progress } from "@/components/ui/progress"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Upload, FileAudio, Loader2, CheckCircle, AlertCircle, FileText, Subtitles, Play, Pause, Volume2, Languages } from "lucide-react"

interface TranscriptionResult {
  srt?: string
  txt?: string
  detected_language?: string
  [key: string]: any
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
  const [activeTab, setActiveTab] = useState<'srt' | 'txt'>('txt')
  const [audioUrl, setAudioUrl] = useState<string | null>(null)

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
      if (droppedFile.type.startsWith("audio/")) {
        setFile(droppedFile)
        setError(null)
        const url = URL.createObjectURL(droppedFile)
        setAudioUrl(url)
      } else {
        setError("Please select an audio file")
      }
    }
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      if (selectedFile.type.startsWith("audio/")) {
        setFile(selectedFile)
        setError(null)
        const url = URL.createObjectURL(selectedFile)
        setAudioUrl(url)
      } else {
        setError("Please select an audio file")
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!file) {
      setError("Please select a file")
      return
    }

    setIsLoading(true)
    setError(null)
    setResult(null)

    try {
      const formData = new FormData()
      formData.append("file", file)
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
          throw new Error(`Validation error: ${errorMessages}`)
        }
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data: TranscriptionResult = await response.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred during transcription")
    } finally {
      setIsLoading(false)
    }
  }

  const resetForm = () => {
    setFile(null)
    setLanguage("auto")
    setResult(null)
    setError(null)
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl)
      setAudioUrl(null)
    }
  }

  return (
    <div className="container mx-auto py-8 px-4 max-w-6xl">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold mb-2">音檔轉錄工具</h1>
        <p className="text-muted-foreground">上傳音檔文件獲取準確的轉錄結果</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Upload Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="w-5 h-5" />
              上傳音檔文件
            </CardTitle>
            <CardDescription>選擇或拖拽音檔文件進行轉錄</CardDescription>
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
                <Input id="file-upload" type="file" accept="audio/*" onChange={handleFileChange} className="hidden" />
              </div>
              
              {/* Language Selection */}
              <div className="space-y-2">
                <Label htmlFor="language-select" className="flex items-center gap-2">
                  <Languages className="w-4 h-4" />
                  選擇語言
                </Label>
                <Select value={language} onValueChange={setLanguage}>
                  <SelectTrigger>
                    <SelectValue placeholder="選擇語言或自動偵測" />
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
                  選擇音檔的語言，或留空讓系統自動偵測
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
                      <audio
                        controls
                        className="w-full"
                        preload="metadata"
                      >
                        <source src={audioUrl} type={file.type} />
                        您的瀏覽器不支持音檔播放器。
                      </audio>
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
              </div>

              {isLoading && (
                <div className="space-y-2">
                  <Progress value={undefined} className="w-full" />
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
                    <span className="text-sm font-medium">偵測語言:</span>
                    <span className="text-sm text-muted-foreground">
                      {commonLanguages.find(lang => lang.code === result.detected_language)?.name || result.detected_language}
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
                    readOnly
                    className="min-h-[300px] resize-none font-mono text-sm"
                    placeholder={activeTab === 'txt' ? '轉錄文本將在這裡顯示...' : 'SRT字幕將在這裡顯示...'}
                  />
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2">
                  <Button
                    onClick={() => {
                      const text = activeTab === 'txt' ? result.txt || '' : result.srt || ''
                      navigator.clipboard.writeText(text)
                    }}
                    className="flex-1"
                  >
                    複製到剪貼板
                  </Button>
                  <Button
                    onClick={() => {
                      const text = activeTab === 'txt' ? result.txt || '' : result.srt || ''
                      const blob = new Blob([text], { type: 'text/plain' })
                      const url = URL.createObjectURL(blob)
                      const a = document.createElement('a')
                      a.href = url
                      a.download = `transcription.${activeTab}`
                      document.body.appendChild(a)
                      a.click()
                      document.body.removeChild(a)
                      URL.revokeObjectURL(url)
                    }}
                    variant="outline"
                    className="flex-1"
                  >
                    下載文件
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <FileAudio className="w-12 h-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">上傳音檔文件以查看轉錄結果</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
