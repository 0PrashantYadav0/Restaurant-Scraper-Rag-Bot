"use client"

import type React from "react"

import { useState, useEffect, useRef } from "react"
import { Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import type { Restaurant } from "@/types/restaurant"

interface ChatMessage {
  role: "user" | "assistant"
  content: string
}

interface WebSocketChatProps {
  selectedRestaurant: Restaurant | null
}

export default function WebSocketChat({ selectedRestaurant }: WebSocketChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: selectedRestaurant
        ? `Hello! Ask me anything about ${selectedRestaurant.name}!`
        : "Hello! Let's chat! Just ask me anything about restaurants!",
    },
  ])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  // Connect to WebSocket
  useEffect(() => {
    const connectWebSocket = () => {
      let wsUrl;
      if (!selectedRestaurant) {
        wsUrl = `/api/ws/chat`
      } else {
        wsUrl = `/api/ws/chat/${selectedRestaurant.id}`
      }
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log("WebSocket connected")
        setIsConnected(true)
      }

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)

        if (data.error) {
          console.error("WebSocket error:", data.error)
          setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${data.error}` }])
          setIsLoading(false)
          return
        }

        if (data.session_id && !sessionId) {
          setSessionId(data.session_id)
        }

        if (data.response) {
          setMessages((prev) => [...prev, { role: "assistant", content: data.response }])
          setIsLoading(false)
        }
      }

      ws.onclose = () => {
        console.log("WebSocket disconnected")
        setIsConnected(false)
        // Try to reconnect after a delay
        setTimeout(() => {
          if (wsRef.current?.readyState !== WebSocket.OPEN) {
            connectWebSocket()
          }
        }, 3000)
      }

      ws.onerror = (error) => {
        console.error("WebSocket error:", error)
        setIsConnected(false)
      }

      wsRef.current = ws
    }

    connectWebSocket()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  // Update welcome message when selected restaurant changes
  useEffect(() => {
    if (selectedRestaurant) {
      setMessages([
        {
          role: "assistant",
          content: `Hello! Ask me anything about ${selectedRestaurant.name}!`,
        },
      ])
    }
  }, [selectedRestaurant])

  // Scroll to bottom when messages change
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector("[data-radix-scroll-area-viewport]")
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight
      }
    }
  }, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!input.trim() || !isConnected || isLoading) return

    const userMessage = input.trim()
    setInput("")

    // Add user message to chat
    setMessages((prev) => [...prev, { role: "user", content: userMessage }])

    // Show loading state
    setIsLoading(true)

    // Send message via WebSocket
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          message: userMessage,
          restaurant_id: selectedRestaurant?.id,
          session_id: sessionId,
        }),
      )
    } else {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "WebSocket connection is not available. Please try again later." },
      ])
      setIsLoading(false)
    }
  }

  return (
    < >
      <CardHeader className="flex flex-row items-center justify-between px-6 py-2 m-0">
        <CardTitle>
          {selectedRestaurant ? `Chat about ${selectedRestaurant.name}` : "Restaurant Assistant"}
          {!isConnected && " (Connecting...)"}
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0 m-0">
        <ScrollArea className="h-[calc(100vh-280px)]" ref={scrollAreaRef}>
          <div className="flex flex-col gap-4 p-4">
            {messages.map((message, index) => (
              <div key={index} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-2 ${message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                    }`}
                >
                  {message.content}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="max-w-[80%] rounded-lg bg-muted px-4 py-2">
                  <div className="flex gap-1">
                    <div className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground"></div>
                    <div className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground delay-75"></div>
                    <div className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground delay-150"></div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
      <CardFooter className="py-2 px-4 m-0">
        <form onSubmit={handleSubmit} className="flex gap-2 w-full">
          <Input
            placeholder={`Ask about ${selectedRestaurant?.name || "restaurants"}...`}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading || !isConnected}
            className="flex-1 h-10"
          />
          <Button type="submit" disabled={isLoading || !input.trim() || !isConnected}>
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </CardFooter>
    </>
  )
}
