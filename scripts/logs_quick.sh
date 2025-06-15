#!/bin/bash
# Quick log viewer aliases for MedEdBot

# Live logs without health checks
alias medlogs='sudo docker logs -f mededbot-v4 2>&1 | grep -v "HEAD / HTTP"'

# Show only important events
alias medimportant='sudo docker logs -f mededbot-v4 2>&1 | grep -E "(User|Gemini|ERROR|✅|📧|🎯|🔊)"'

# Show errors only
alias mederrors='sudo docker logs -f mededbot-v4 2>&1 | grep -E "(ERROR|Failed|Exception)"'

# Show last 50 meaningful lines
alias medrecent='sudo docker logs mededbot-v4 2>&1 | grep -v "HEAD / HTTP" | tail -50'

# Follow logs with timestamp
alias medtime='sudo docker logs -f -t mededbot-v4 | grep -v "HEAD / HTTP"'

# Quick stats
medstats() {
    echo "=== MedEdBot Stats ==="
    echo "Container Status:"
    sudo docker ps | grep mededbot-v4
    echo ""
    echo "Recent Activity:"
    sudo docker logs --tail 100 mededbot-v4 2>&1 | grep -c "User"
    echo "user messages in last 100 lines"
    echo ""
    echo "Recent Errors:"
    sudo docker logs --tail 100 mededbot-v4 2>&1 | grep -c "ERROR"
    echo "errors in last 100 lines"
}

# Usage instructions
echo "MedEdBot Log Commands:"
echo "  medlogs      - Live logs (no health checks)"
echo "  medimportant - Important events only"
echo "  mederrors    - Errors only"
echo "  medrecent    - Last 50 meaningful lines"
echo "  medtime      - Logs with timestamps"
echo "  medstats     - Quick statistics"