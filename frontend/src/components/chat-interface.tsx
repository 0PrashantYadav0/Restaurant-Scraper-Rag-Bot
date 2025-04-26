import type React from "react"

import { useState, useRef, useEffect } from "react"
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

interface ChatInterfaceProps {
  selectedRestaurant: Restaurant | null
}

export default function ChatInterface({ selectedRestaurant }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: selectedRestaurant
        ? `Hello! Ask me anything about ${selectedRestaurant.name}!`
        : "Hello! What you want to know about? Just ask me anything about Restaurants given!",
    },
  ])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const scrollAreaRef = useRef<HTMLDivElement>(null)

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!input.trim()) return

    const userMessage = input.trim()
    setInput("")

    // Add user message to chat
    setMessages((prev) => [...prev, { role: "user", content: userMessage }])

    // Show loading state
    setIsLoading(true)

    try {
      let response: Response;
      if (!selectedRestaurant) {
        response = await fetch(`/api/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: userMessage,
            restaurant_id: null,
            session_id: sessionId,
          }),
        })
      } else {
        response = await fetch(`/api/chat/${selectedRestaurant.id}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: userMessage,
            restaurant_id: selectedRestaurant.id,
            session_id: sessionId,
          }),
        })
      }
      const data = await response.json()

      if (response.ok) {
        // Save session ID for future requests
        if (data.session_id && !sessionId) {
          setSessionId(data.session_id)
        }

        // Add assistant response to chat
        setMessages((prev) => [...prev, { role: "assistant", content: data.response }])
      } else {
        // Handle error
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Sorry, I encountered an error. Please try again." },
        ])
      }
    } catch (error) {
      console.error("Error sending message:", error)
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I encountered an error. Please try again." },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  // Function to reset conversation
  const resetConversation = async () => {
    setMessages([
      {
        role: "assistant",
        content: selectedRestaurant
          ? `Hello! Ask me anything about ${selectedRestaurant.name}!`
          : "Hello! How can I help you with restaurants today?",
      },
    ])
    setInput("")
    setSessionId(null)
    setIsLoading(false)
  }

  return (
    <div className="">
      <CardHeader className="flex flex-row items-center justify-between px-6 py-2 m-0">
        <CardTitle>
          {selectedRestaurant ? `Chat about ${selectedRestaurant.name}` : "Restaurant Assistant"}</CardTitle>
        {messages.length > 1 && (
          <Button variant="outline" size="sm" onClick={resetConversation}>
            Reset Chat
          </Button>
        )}
      </CardHeader>
      <CardContent className="p-0 m-0">
        <ScrollArea className="h-[calc(100vh-280px)]" ref={scrollAreaRef}>
          <div className="flex flex-col gap-4 p-4">
            {messages.map((message, index) => (
              <div key={index} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-2 ${
                    message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
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
        <form onSubmit={handleSubmit} className="flex w-full gap-2">
          <Input
            placeholder={`Ask about ${selectedRestaurant?.name || "restaurants"}...`}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            className="flex-1 h-10"
          />
          <Button type="submit" disabled={isLoading || !input.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </CardFooter>
    </div>
  )
}
