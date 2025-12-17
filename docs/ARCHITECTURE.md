```mermaid
graph TD
    subgraph Input_Layer
        User -->|Text Message| Msg[Text Input]
        User -->|Image| Img[Image Input]
        User -->|PDF| Pdf[PDF Input]
        User -->|Audio| Aud[Audio Input]
        User -->|YouTube| Yt[YouTube URL Input]
    end

    subgraph Tool_Layer
        Msg --> FastAPI[FastAPI Server]
        Img --> OCR[OCR (Groq Vision)]
        Pdf --> Parser[PDF Parser (PyPDF)]
        Aud --> Trans[Audio Transcription (Groq Whisper)]
        Yt --> YtAPI[YouTube Transcript API]
        
        OCR --> FastAPI
        Parser --> FastAPI
        Trans --> FastAPI
        YtAPI --> FastAPI
    end

    subgraph Routing_Layer
        FastAPI --> Agent[LangGraph Agent]
        Agent --> Classifier[Intent Classifier (Groq Llama-3)]
        Classifier --> Router{Routing Decision}
        
        Router -->|Ambiguous Intent| Clarify[Clarify Node]
        Clarify -->|Ask Follow-up| User
        
        Router -->|Clear Intent| Execute[Execute Node]
    end

    subgraph Execution_Layer
        Execute --> TaskRouter{Task Router}
        
        TaskRouter --> Sum[Summarization]
        TaskRouter --> SA[Sentiment Analysis]
        TaskRouter --> Code[Code Explanation]
        TaskRouter --> Extract[Text Extraction]
        TaskRouter --> Search[Web Search (DuckDuckGo)]
        TaskRouter --> Conv[Conversational Answer]
    end

    subgraph Output_Layer
        Sum --> Response
        SA --> Response
        Code --> Response
        Extract --> Response
        Search --> Response
        Conv --> Response
        
        Response --> UI[Web Interface HTML/CSS/JS]
    end
    
    style Input_Layer fill:#e0f2f1,stroke:#004d40
    style Tool_Layer fill:#f3e5f5,stroke:#4a148c
    style Routing_Layer fill:#fbe9e7,stroke:#bf360c
    style Execution_Layer fill:#e1f5fe,stroke:#01579b
    style Output_Layer fill:#f1f8e9,stroke:#33691e
```
