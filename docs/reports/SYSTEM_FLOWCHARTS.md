# MedEdBot System Flowcharts and Diagrams

## 1. Master System Flow

```mermaid
graph TB
    START([User Starts Interaction]) --> INPUT{Input Type?}
    
    INPUT -->|Text Message| TEXT_PROCESS[Text Processing]
    INPUT -->|Voice Message| VOICE_PROCESS[Voice Processing]
    
    VOICE_PROCESS --> STT[Speech-to-Text<br/>Gemini API]
    STT --> TEXT_PROCESS
    
    TEXT_PROCESS --> SESSION[Retrieve/Create<br/>User Session]
    SESSION --> CHECK_STATE{Session<br/>State?}
    
    CHECK_STATE -->|Not Started| WELCOME[Show Welcome<br/>Message]
    WELCOME --> QUICK_REPLY[Display 'Start'<br/>Button]
    
    CHECK_STATE -->|Started, No Mode| MODE_SELECT[Mode Selection<br/>Menu]
    MODE_SELECT --> MODE_CHOICE{User<br/>Choice?}
    
    MODE_CHOICE -->|Education| EDU_MODE[Education Mode<br/>Handler]
    MODE_CHOICE -->|Chat| CHAT_MODE[Chat Mode<br/>Handler]
    
    CHECK_STATE -->|Mode Selected| ROUTE{Route by<br/>Mode}
    ROUTE -->|Education| EDU_MODE
    ROUTE -->|Chat| CHAT_MODE
    
    EDU_MODE --> EDU_RESPONSE[Generate<br/>Response]
    CHAT_MODE --> CHAT_RESPONSE[Generate<br/>Response]
    
    EDU_RESPONSE --> FORMAT[Format Response<br/>with Bubbles]
    CHAT_RESPONSE --> FORMAT
    
    FORMAT --> SEND[Send to User<br/>via LINE]
    SEND --> LOG[Log Interaction<br/>Async]
    LOG --> END([End])
    
    style START fill:#e1f5e1
    style END fill:#ffe1e1
    style STT fill:#fff3cd
    style EDU_MODE fill:#cfe2ff
    style CHAT_MODE fill:#cfe2ff
```

## 2. Chat Mode Detailed Flow

```mermaid
flowchart TB
    subgraph "Chat Mode Initialization"
        CHAT_START([Chat Mode Selected]) --> LANG_CHECK{Language<br/>Selected?}
        LANG_CHECK -->|No| LANG_PROMPT[Prompt for<br/>Language Selection]
        LANG_PROMPT --> LANG_INPUT[User Selects<br/>Language]
        LANG_INPUT --> SAVE_LANG[Save Target<br/>Language]
        LANG_CHECK -->|Yes| READY[Ready for<br/>Translation]
        SAVE_LANG --> READY
    end
    
    subgraph "Message Processing"
        READY --> MSG_INPUT[Receive User<br/>Message]
        MSG_INPUT --> PLAINIFY[Plainify Text<br/>Remove URLs/Unsafe]
        PLAINIFY --> DETECT_LANG{Target<br/>Language?}
    end
    
    subgraph "Translation Path Selection"
        DETECT_LANG -->|Taiwanese/Taigi| TAIGI_PATH[Taigi Service<br/>Path]
        DETECT_LANG -->|Other Languages| GEMINI_PATH[Gemini API<br/>Path]
    end
    
    subgraph "Taigi Processing"
        TAIGI_PATH --> TAIGI_API[Call NYCU<br/>Taigi API]
        TAIGI_API --> TAIGI_CHECK{Success?}
        TAIGI_CHECK -->|Yes| TAIGI_RESULT[TLPA<br/>Romanization]
        TAIGI_CHECK -->|No| TAIGI_ERROR[Error<br/>Message]
    end
    
    subgraph "Gemini Processing"
        GEMINI_PATH --> GEMINI_API[Call Gemini<br/>Translate API]
        GEMINI_API --> GEMINI_CHECK{Success?}
        GEMINI_CHECK -->|Yes| GEMINI_RESULT[Translated<br/>Text]
        GEMINI_CHECK -->|No| GEMINI_ERROR[Error<br/>Message]
    end
    
    subgraph "Response Generation"
        TAIGI_RESULT --> RESPONSE[Format<br/>Response]
        GEMINI_RESULT --> RESPONSE
        TAIGI_ERROR --> RESPONSE
        GEMINI_ERROR --> RESPONSE
        RESPONSE --> TTS_CHECK{User Requests<br/>TTS?}
    end
    
    subgraph "TTS Generation"
        TTS_CHECK -->|Yes + Taigi| TAIGI_TTS[Generate Taigi<br/>Audio]
        TTS_CHECK -->|Yes + Other| GEMINI_TTS[Generate Gemini<br/>Audio]
        TTS_CHECK -->|No| NO_TTS[Text Only<br/>Response]
        TAIGI_TTS --> AUDIO_READY[Audio File<br/>Ready]
        GEMINI_TTS --> AUDIO_READY
    end
    
    subgraph "Final Output"
        AUDIO_READY --> FINAL[Send Response<br/>+ Audio]
        NO_TTS --> FINAL
        FINAL --> CHAT_END([Continue or<br/>New Chat])
    end
    
    style CHAT_START fill:#e1f5e1
    style CHAT_END fill:#ffe1e1
    style TAIGI_PATH fill:#fff3cd
    style GEMINI_PATH fill:#cfe2ff
```

## 3. Education Mode Detailed Flow

```mermaid
flowchart TB
    subgraph "Education Mode Start"
        EDU_START([Education Mode<br/>Selected]) --> TOPIC_PROMPT[Show Topic<br/>Suggestions]
        TOPIC_PROMPT --> TOPIC_INPUT[User Enters<br/>Health Topic]
    end
    
    subgraph "Content Generation"
        TOPIC_INPUT --> GEN_CHECK{Content<br/>Exists?}
        GEN_CHECK -->|No| GENERATE[Generate Chinese<br/>Content via Gemini]
        GEN_CHECK -->|Yes| SHOW_OPTIONS[Show Action<br/>Options]
        GENERATE --> STORE[Store in<br/>Session]
        STORE --> GET_REFS[Extract<br/>References]
        GET_REFS --> SHOW_OPTIONS
    end
    
    subgraph "User Actions"
        SHOW_OPTIONS --> ACTION{User<br/>Choice?}
        ACTION -->|Modify| MODIFY_FLOW
        ACTION -->|Translate| TRANS_FLOW
        ACTION -->|Email| EMAIL_FLOW
        ACTION -->|New| NEW_FLOW
    end
    
    subgraph "Modify Flow"
        MODIFY_FLOW[Modify Request] --> MOD_INPUT[User Describes<br/>Changes]
        MOD_INPUT --> MOD_GEN[Regenerate with<br/>Modifications]
        MOD_GEN --> MOD_UPDATE[Update Session<br/>Content]
        MOD_UPDATE --> SHOW_OPTIONS
    end
    
    subgraph "Translate Flow"
        TRANS_FLOW[Translate Request] --> LANG_SELECT[Select Target<br/>Language]
        LANG_SELECT --> LANG_CHECK{Is Taigi?}
        LANG_CHECK -->|Yes| BLOCK_TAIGI[Show Error:<br/>Taigi Not Supported]
        LANG_CHECK -->|No| TRANS_GEN[Generate Translation<br/>via Gemini]
        TRANS_GEN --> TRANS_STORE[Store Translation]
        TRANS_STORE --> SHOW_OPTIONS
        BLOCK_TAIGI --> SHOW_OPTIONS
    end
    
    subgraph "Email Flow"
        EMAIL_FLOW[Email Request] --> EMAIL_INPUT[Enter Email<br/>Address]
        EMAIL_INPUT --> VALIDATE[Validate Email<br/>Format & MX]
        VALIDATE --> SEND{Valid?}
        SEND -->|Yes| SEND_EMAIL[Send Content<br/>via Email]
        SEND -->|No| EMAIL_ERROR[Show Error<br/>Message]
        SEND_EMAIL --> CONFIRM[Show Success<br/>Message]
        CONFIRM --> SHOW_OPTIONS
        EMAIL_ERROR --> EMAIL_INPUT
    end
    
    subgraph "New Topic Flow"
        NEW_FLOW[New Request] --> CLEAR[Clear Session<br/>Content]
        CLEAR --> TOPIC_PROMPT
    end
    
    style EDU_START fill:#e1f5e1
    style GENERATE fill:#fff3cd
    style BLOCK_TAIGI fill:#ffe1e1
```

## 4. Voice Processing Flow

```mermaid
flowchart LR
    subgraph "Voice Input Processing"
        VOICE([Voice Message<br/>Received]) --> CHECK_MODE{Mode &<br/>Language Set?}
        CHECK_MODE -->|No| REJECT[Reject with<br/>Instructions]
        CHECK_MODE -->|Yes| DOWNLOAD[Download Audio<br/>from LINE]
        
        DOWNLOAD --> SAVE[Save to<br/>Temp File]
        SAVE --> SIZE_CHECK{Size<br/>< 10MB?}
        SIZE_CHECK -->|No| SIZE_ERROR[Error:<br/>File Too Large]
        SIZE_CHECK -->|Yes| TRANSCRIBE[Transcribe via<br/>Gemini STT]
        
        TRANSCRIBE --> CHECK_STT{Success?}
        CHECK_STT -->|No| STT_ERROR[Error:<br/>Transcription Failed]
        CHECK_STT -->|Yes| GET_TEXT[Extract<br/>Text]
        
        GET_TEXT --> DELETE[Delete Audio<br/>File Immediately]
        DELETE --> PROCESS[Process as<br/>Text Input]
        
        PROCESS --> MEDCHAT[Send to<br/>MedChat Handler]
        MEDCHAT --> RESULT[Get Translation<br/>Result]
        
        RESULT --> FORMAT[Add Voice<br/>Indicator 🎤]
        FORMAT --> SEND[Send Response<br/>to User]
    end
    
    style VOICE fill:#e1f5e1
    style REJECT fill:#ffe1e1
    style SIZE_ERROR fill:#ffe1e1
    style STT_ERROR fill:#ffe1e1
    style DELETE fill:#fff3cd
```

## 5. TTS Generation Flow

```mermaid
flowchart TB
    subgraph "TTS Request Processing"
        TTS_START([User Clicks<br/>朗讀/Speak]) --> CHECK_CONTENT{Translation<br/>Exists?}
        CHECK_CONTENT -->|No| NO_CONTENT[Error: No Content<br/>to Speak]
        CHECK_CONTENT -->|Yes| CHECK_AUDIO{Audio Already<br/>Generated?}
        
        CHECK_AUDIO -->|Yes| RETURN_EXISTING[Return Existing<br/>Audio URL]
        CHECK_AUDIO -->|No| DETECT_LANG{Last Translation<br/>Language?}
    end
    
    subgraph "Language-Specific TTS"
        DETECT_LANG -->|Taiwanese/Taigi| TAIGI_TTS_FLOW
        DETECT_LANG -->|Other Languages| GEMINI_TTS_FLOW
    end
    
    subgraph "Taigi TTS Process"
        TAIGI_TTS_FLOW[Taigi TTS Path] --> GET_CHINESE[Get Original<br/>Chinese Text]
        GET_CHINESE --> CHECK_CHINESE{Chinese Text<br/>Available?}
        CHECK_CHINESE -->|No| TAIGI_ERROR[Error: No Source<br/>for Taigi TTS]
        CHECK_CHINESE -->|Yes| CALL_TAIGI[Call NYCU<br/>Taigi TTS API]
        
        CALL_TAIGI --> TAIGI_RESULT{Success?}
        TAIGI_RESULT -->|Yes| TAIGI_AUDIO[Save Taigi<br/>Audio File]
        TAIGI_RESULT -->|No| TAIGI_TTS_ERROR[Error: TTS<br/>Generation Failed]
        
        TAIGI_AUDIO --> SET_CREDIT[Set Credit<br/>Flag = True]
    end
    
    subgraph "Gemini TTS Process"
        GEMINI_TTS_FLOW[Gemini TTS Path] --> GET_TRANS[Get Translated<br/>Text]
        GET_TRANS --> CALL_GEMINI[Call Gemini<br/>TTS API]
        
        CALL_GEMINI --> GEMINI_RESULT{Success?}
        GEMINI_RESULT -->|Yes| GEMINI_AUDIO[Save Audio<br/>File]
        GEMINI_RESULT -->|No| GEMINI_TTS_ERROR[Error: TTS<br/>Generation Failed]
    end
    
    subgraph "Audio Delivery"
        TAIGI_AUDIO --> STORE_URL[Store Audio URL<br/>in Session]
        GEMINI_AUDIO --> STORE_URL
        SET_CREDIT --> STORE_URL
        
        STORE_URL --> CALC_DUR[Calculate Audio<br/>Duration]
        CALC_DUR --> PREPARE[Prepare Audio<br/>Message]
        
        PREPARE --> CHECK_CREDIT{Show Taigi<br/>Credit?}
        CHECK_CREDIT -->|Yes| WITH_CREDIT[Send Credit Bubble<br/>+ Audio]
        CHECK_CREDIT -->|No| WITHOUT_CREDIT[Send Audio<br/>Only]
        
        RETURN_EXISTING --> WITHOUT_CREDIT
    end
    
    style TTS_START fill:#e1f5e1
    style NO_CONTENT fill:#ffe1e1
    style TAIGI_ERROR fill:#ffe1e1
    style TAIGI_TTS_ERROR fill:#ffe1e1
    style GEMINI_TTS_ERROR fill:#ffe1e1
```

## 6. Session Management Flow

```mermaid
stateDiagram-v2
    [*] --> NewUser: First Interaction
    
    NewUser --> CreateSession: Initialize Session
    CreateSession --> NotStarted: Set started=false
    
    NotStarted --> Started: User clicks "開始"
    Started --> ModeSelection: Set started=true
    
    ModeSelection --> EducationMode: Select "衛教"
    ModeSelection --> ChatMode: Select "醫療翻譯"
    
    state ChatMode {
        [*] --> AwaitingLanguage: Set mode=chat
        AwaitingLanguage --> LanguageSet: User selects language
        LanguageSet --> ReadyToTranslate: Save target language
        ReadyToTranslate --> Processing: Receive message
        Processing --> ReadyToTranslate: Show result
    }
    
    state EducationMode {
        [*] --> AwaitingTopic: Set mode=edu
        AwaitingTopic --> ContentGenerated: Generate content
        ContentGenerated --> ShowingOptions: Display actions
        
        ShowingOptions --> Modifying: User selects modify
        Modifying --> ContentGenerated: Update content
        
        ShowingOptions --> Translating: User selects translate
        Translating --> ContentGenerated: Add translation
        
        ShowingOptions --> Emailing: User selects email
        Emailing --> ShowingOptions: Send complete
    }
    
    ChatMode --> Reset: User clicks "新對話"
    EducationMode --> Reset: User clicks "新對話"
    Reset --> NotStarted: Clear session
    
    NotStarted --> SessionExpired: 24 hours inactive
    Started --> SessionExpired: 24 hours inactive
    ModeSelection --> SessionExpired: 24 hours inactive
    ChatMode --> SessionExpired: 24 hours inactive
    EducationMode --> SessionExpired: 24 hours inactive
    
    SessionExpired --> [*]: Delete session
```

## 7. Error Handling and Recovery Flow

```mermaid
flowchart TB
    subgraph "Error Detection"
        REQUEST([User Request]) --> PROCESS[Process Request]
        PROCESS --> ERROR{Error<br/>Occurred?}
        ERROR -->|No| SUCCESS[Return Success<br/>Response]
        ERROR -->|Yes| CLASSIFY[Classify Error<br/>Type]
    end
    
    subgraph "Error Classification"
        CLASSIFY --> TYPE{Error<br/>Type?}
        TYPE -->|Network| NETWORK_ERR[Network Error<br/>Handler]
        TYPE -->|Rate Limit| RATE_ERR[Rate Limit<br/>Handler]
        TYPE -->|Timeout| TIMEOUT_ERR[Timeout Error<br/>Handler]
        TYPE -->|Invalid Input| INPUT_ERR[Input Error<br/>Handler]
        TYPE -->|Service Down| SERVICE_ERR[Service Error<br/>Handler]
    end
    
    subgraph "Network Errors"
        NETWORK_ERR --> NET_RETRY{Retry<br/>Count < 3?}
        NET_RETRY -->|Yes| NET_WAIT[Wait 3s]
        NET_WAIT --> PROCESS
        NET_RETRY -->|No| NET_MSG[Show Network<br/>Error Message]
    end
    
    subgraph "Rate Limit Errors"
        RATE_ERR --> CALC_WAIT[Calculate Wait<br/>Time]
        CALC_WAIT --> RATE_MSG[Show Rate Limit<br/>Message + Time]
    end
    
    subgraph "Timeout Errors"
        TIMEOUT_ERR --> TIME_CHECK{Service<br/>Type?}
        TIME_CHECK -->|Gemini| GEM_TIMEOUT[45s Timeout<br/>Message]
        TIME_CHECK -->|Taigi| TAIGI_TIMEOUT[60s Timeout<br/>Message]
    end
    
    subgraph "Circuit Breaker"
        SERVICE_ERR --> CIRCUIT{Circuit<br/>State?}
        CIRCUIT -->|Closed| INCR_FAIL[Increment<br/>Failure Count]
        INCR_FAIL --> CHECK_THRESH{Threshold<br/>Reached?}
        CHECK_THRESH -->|Yes| OPEN_CIRCUIT[Open Circuit<br/>30s]
        CHECK_THRESH -->|No| SERVICE_MSG[Show Service<br/>Error]
        CIRCUIT -->|Open| CIRCUIT_MSG[Show Service<br/>Unavailable]
        OPEN_CIRCUIT --> CIRCUIT_MSG
    end
    
    subgraph "User Feedback"
        NET_MSG --> SUGGEST[Suggest<br/>Retry]
        RATE_MSG --> SUGGEST
        GEM_TIMEOUT --> SUGGEST
        TAIGI_TIMEOUT --> SUGGEST
        SERVICE_MSG --> SUGGEST
        CIRCUIT_MSG --> SUGGEST
        INPUT_ERR --> CORRECT[Show Correct<br/>Format]
        
        SUGGEST --> END([User Decides<br/>Next Action])
        CORRECT --> END
    end
    
    style REQUEST fill:#e1f5e1
    style SUCCESS fill:#cfe2ff
    style END fill:#ffe1e1
```

## 8. Data Flow Architecture

```mermaid
graph TB
    subgraph "Input Sources"
        USER[User Input]
        LINE_API[LINE Platform API]
        VOICE_API[Voice Input API]
    end
    
    subgraph "Processing Layer"
        WEBHOOK[Webhook Handler]
        AUTH[Authentication]
        VALIDATOR[Input Validator]
        ROUTER[Request Router]
    end
    
    subgraph "Business Logic"
        SESSION_MGR[Session Manager]
        CHAT_HANDLER[Chat Handler]
        EDU_HANDLER[Education Handler]
        CMD_PARSER[Command Parser]
    end
    
    subgraph "AI Services"
        GEMINI[Gemini API<br/>- Translation<br/>- STT/TTS<br/>- Content Gen]
        TAIGI[NYCU Taigi<br/>- Translation<br/>- TTS]
    end
    
    subgraph "Data Storage"
        MEMORY[Memory Storage<br/>- Audio Files<br/>- Session Data]
        DATABASE[(PostgreSQL<br/>- Logs<br/>- Analytics)]
        TEMP[Temp Storage<br/>- Voice Files]
    end
    
    subgraph "Output Layer"
        FORMATTER[Response Formatter]
        BUBBLE_GEN[Bubble Generator]
        AUDIO_PREP[Audio Preparer]
    end
    
    USER --> LINE_API
    VOICE_API --> LINE_API
    LINE_API --> WEBHOOK
    WEBHOOK --> AUTH
    AUTH --> VALIDATOR
    VALIDATOR --> ROUTER
    
    ROUTER --> SESSION_MGR
    SESSION_MGR --> CHAT_HANDLER
    SESSION_MGR --> EDU_HANDLER
    ROUTER --> CMD_PARSER
    
    CHAT_HANDLER --> GEMINI
    CHAT_HANDLER --> TAIGI
    EDU_HANDLER --> GEMINI
    
    CHAT_HANDLER --> MEMORY
    EDU_HANDLER --> MEMORY
    SESSION_MGR --> DATABASE
    
    VOICE_API --> TEMP
    GEMINI --> TEMP
    TAIGI --> TEMP
    
    CHAT_HANDLER --> FORMATTER
    EDU_HANDLER --> FORMATTER
    FORMATTER --> BUBBLE_GEN
    FORMATTER --> AUDIO_PREP
    
    BUBBLE_GEN --> LINE_API
    AUDIO_PREP --> LINE_API
    
    style USER fill:#e1f5e1
    style GEMINI fill:#fff3cd
    style TAIGI fill:#fff3cd
    style DATABASE fill:#cfe2ff
```

## 9. Concurrency Control Flow

```mermaid
flowchart TB
    subgraph "Request Entry"
        REQ1[User 1 Request]
        REQ2[User 2 Request]
        REQ3[User 1 Request 2]
        
        REQ1 --> QUEUE[Request Queue]
        REQ2 --> QUEUE
        REQ3 --> QUEUE
    end
    
    subgraph "Concurrency Manager"
        QUEUE --> DISPATCHER[Request Dispatcher]
        DISPATCHER --> CHECK_USER{Same<br/>User?}
        
        CHECK_USER -->|Different Users| PARALLEL[Parallel Processing]
        CHECK_USER -->|Same User| SEQUENTIAL[Sequential Queue]
    end
    
    subgraph "Parallel Processing"
        PARALLEL --> WORKER1[Worker Thread 1<br/>User 1]
        PARALLEL --> WORKER2[Worker Thread 2<br/>User 2]
        
        WORKER1 --> LOCK1[Acquire User 1<br/>Session Lock]
        WORKER2 --> LOCK2[Acquire User 2<br/>Session Lock]
    end
    
    subgraph "Sequential Processing"
        SEQUENTIAL --> WAIT[Wait for Previous<br/>Request]
        WAIT --> WORKER3[Worker Thread<br/>Process Next]
        WORKER3 --> LOCK3[Acquire User<br/>Session Lock]
    end
    
    subgraph "Resource Protection"
        LOCK1 --> RATE1[Check Rate<br/>Limit]
        LOCK2 --> RATE2[Check Rate<br/>Limit]
        LOCK3 --> RATE3[Check Rate<br/>Limit]
        
        RATE1 --> PROCESS1[Process Request]
        RATE2 --> PROCESS2[Process Request]
        RATE3 --> PROCESS3[Process Request]
    end
    
    subgraph "Cleanup"
        PROCESS1 --> RELEASE1[Release Lock]
        PROCESS2 --> RELEASE2[Release Lock]
        PROCESS3 --> RELEASE3[Release Lock]
        
        RELEASE1 --> RESP1[Send Response]
        RELEASE2 --> RESP2[Send Response]
        RELEASE3 --> RESP3[Send Response]
    end
    
    style REQ1 fill:#e1f5e1
    style REQ2 fill:#cfe2ff
    style REQ3 fill:#e1f5e1
```

## 10. Quick Reference - Command Flow

```mermaid
graph LR
    subgraph "Global Commands"
        NEW[new/開始] --> RESET[Reset Session]
        SPEAK[speak/朗讀] --> TTS[Generate Audio]
    end
    
    subgraph "Education Mode Commands"
        MODIFY[modify/修改] --> MOD_FLOW[Modification Flow]
        TRANSLATE[translate/翻譯] --> TRANS_FLOW[Translation Flow]
        MAIL[mail/寄送] --> EMAIL_FLOW[Email Flow]
    end
    
    subgraph "Chat Mode Commands"
        CONTINUE[繼續翻譯] --> KEEP_LANG[Keep Language<br/>New Message]
        CHANGE[更改語言] --> CHANGE_LANG[Change Target<br/>Language]
    end
    
    style NEW fill:#e1f5e1
    style SPEAK fill:#fff3cd
    style MODIFY fill:#cfe2ff
    style TRANSLATE fill:#cfe2ff
    style MAIL fill:#cfe2ff
```

---

These flowcharts provide comprehensive visual documentation of:
1. Overall system architecture and flow
2. Mode-specific processing paths
3. Error handling and recovery mechanisms
4. Concurrency control systems
5. Data flow patterns
6. Command processing flows

Each diagram can be rendered using Mermaid-compatible tools and provides clear technical documentation suitable for patent filing purposes.