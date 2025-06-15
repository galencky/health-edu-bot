#!/bin/bash
# MedEdBot Log Viewer Script for Synology NAS
# Place this in /volume1/docker/mededbot-v4/ and run with: ./watch_logs.sh

# Colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to show menu
show_menu() {
    echo -e "${CYAN}=== MedEdBot Log Viewer ===${NC}"
    echo "1) Show all logs (live)"
    echo "2) Show logs without health checks"
    echo "3) Show only user interactions"
    echo "4) Show only errors and warnings"
    echo "5) Show last 50 lines"
    echo "6) Search logs for specific text"
    echo "7) Show logs with timestamps"
    echo "8) Export logs to file"
    echo "9) Clear screen and show menu"
    echo "0) Exit"
    echo -e "${YELLOW}Choose an option:${NC} "
}

# Main script
cd /volume1/docker/mededbot-v4 2>/dev/null || cd $(dirname $0)

while true; do
    show_menu
    read -r choice
    
    case $choice in
        1)
            echo -e "${GREEN}Showing all logs (Ctrl+C to stop)...${NC}"
            sudo docker logs -f mededbot-v4
            ;;
        
        2)
            echo -e "${GREEN}Showing logs without health checks (Ctrl+C to stop)...${NC}"
            sudo docker logs -f mededbot-v4 2>&1 | grep -v -E "(HEAD|GET) / HTTP/1.1.*200"
            ;;
        
        3)
            echo -e "${GREEN}Showing user interactions only (Ctrl+C to stop)...${NC}"
            sudo docker logs -f mededbot-v4 2>&1 | grep -E "(User|Gemini|STT|TTS|📧|✅|🎯|🔊)" --color=always
            ;;
        
        4)
            echo -e "${RED}Showing errors and warnings (Ctrl+C to stop)...${NC}"
            sudo docker logs -f mededbot-v4 2>&1 | grep -E "(ERROR|WARNING|Failed|Error|Exception)" --color=always
            ;;
        
        5)
            echo -e "${GREEN}Showing last 50 lines...${NC}"
            sudo docker logs --tail 50 mededbot-v4
            echo -e "${YELLOW}Press Enter to continue...${NC}"
            read
            ;;
        
        6)
            echo -e "${YELLOW}Enter search term:${NC} "
            read -r search_term
            echo -e "${GREEN}Searching for '$search_term'...${NC}"
            sudo docker logs mededbot-v4 2>&1 | grep -i "$search_term" --color=always
            echo -e "${YELLOW}Press Enter to continue...${NC}"
            read
            ;;
        
        7)
            echo -e "${GREEN}Showing logs with timestamps (Ctrl+C to stop)...${NC}"
            sudo docker logs -f -t mededbot-v4
            ;;
        
        8)
            timestamp=$(date +%Y%m%d_%H%M%S)
            logfile="mededbot_logs_$timestamp.txt"
            echo -e "${GREEN}Exporting logs to $logfile...${NC}"
            sudo docker logs mededbot-v4 > "$logfile" 2>&1
            echo -e "${GREEN}Logs exported to: $(pwd)/$logfile${NC}"
            echo -e "${YELLOW}Press Enter to continue...${NC}"
            read
            ;;
        
        9)
            clear
            ;;
        
        0)
            echo -e "${CYAN}Goodbye!${NC}"
            exit 0
            ;;
        
        *)
            echo -e "${RED}Invalid option. Please try again.${NC}"
            sleep 1
            ;;
    esac
done