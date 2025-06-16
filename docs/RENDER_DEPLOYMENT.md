# Deploying MedEdBot to Render

This guide walks you through deploying MedEdBot to Render.com.

## Prerequisites

1. A [Render.com](https://render.com) account
2. A GitHub repository with the MedEdBot code
3. Required API keys and credentials

## Step-by-Step Deployment

### 1. Fork and Prepare Repository

1. Fork this repository to your GitHub account
2. Remove any `.env` files from the repository
3. Ensure `render.yaml` is in the root directory

### 2. Create Render Web Service

1. Log in to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub account if not already connected
4. Select your MedEdBot repository
5. Render will auto-detect the `render.yaml` configuration

### 3. Configure Environment Variables

In the Render dashboard, add these environment variables:

#### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | `AIza...` |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE bot access token | `abc123...` |
| `LINE_CHANNEL_SECRET` | LINE webhook secret | `def456...` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host/db?sslmode=require` |
| `GMAIL_ADDRESS` | Gmail address for sending | `bot@gmail.com` |
| `GMAIL_APP_PASSWORD` | Gmail app-specific password | `abcd efgh ijkl mnop` |
| `BASE_URL` | Your Render URL (after creation) | `https://mededbot.onrender.com` |

#### Optional Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_DRIVE_FOLDER_ID` | Google Drive folder for backups | `1abc...` |
| `GOOGLE_CREDS_B64` | Base64 encoded service account | `eyJ0eXBlIj...` |
| `LOG_LEVEL` | Logging level | `info` |
| `RENDER` | Set to enable Render optimizations | `true` |

### 4. Configure LINE Webhook

1. After deployment, copy your Render URL (e.g., `https://mededbot.onrender.com`)
2. Go to [LINE Developers Console](https://developers.line.biz/)
3. Select your channel
4. Under "Messaging API" settings:
   - Set Webhook URL: `https://mededbot.onrender.com/webhook`
   - Enable webhook
   - Disable auto-reply messages
5. Verify the webhook

### 5. Set Up Database

#### Option A: Use Render PostgreSQL
1. In Render dashboard, create a new PostgreSQL database
2. Copy the connection string to `DATABASE_URL`

#### Option B: Use Neon.tech (Recommended)
1. Create account at [Neon.tech](https://neon.tech)
2. Create new database
3. Copy connection string to `DATABASE_URL`
4. Ensure `?sslmode=require` is in the URL

### 6. Deploy

1. Click "Create Web Service"
2. Render will build and deploy automatically
3. Monitor the deployment logs
4. Once deployed, test the health check: `https://your-app.onrender.com/ping`

## Post-Deployment

### Initialize Database

Run the database initialization by accessing:
```
https://your-app.onrender.com/
```

Check logs to ensure tables are created.

### Test the Bot

1. Add your LINE bot as a friend
2. Send "new" to start
3. Test various commands

### Monitor Performance

- Check Render dashboard for metrics
- Monitor logs for errors
- Set up alerts for downtime

## Troubleshooting

### Bot Not Responding
- Check LINE webhook URL is correct
- Verify all environment variables are set
- Check Render logs for errors

### Audio Files Not Playing
- Ensure `BASE_URL` is set correctly
- Check if using memory storage (ephemeral filesystem)
- Verify Google Drive is configured (if using)

### Database Connection Failed
- Verify `DATABASE_URL` format
- Ensure SSL mode is set
- Check database is accessible

### Memory Issues
- Free tier has 512MB RAM limit
- Consider upgrading if needed
- Monitor memory usage in dashboard

## Optimization Tips

1. **Use Environment Variables**
   - Set `RENDER=true` to enable optimizations
   - Adjust `LOG_LEVEL` to reduce logging

2. **Configure Auto-Deploy**
   - Enable auto-deploy from main branch
   - Set up preview environments for testing

3. **Scale as Needed**
   - Upgrade to paid tier for more resources
   - Add more instances for high traffic

## Cost Considerations

- **Free Tier**: 
  - 512MB RAM
  - Spins down after 15 minutes of inactivity
  - Limited to 750 hours/month

- **Starter Tier ($7/month)**:
  - Always on
  - More resources
  - Better for production use

## Security Notes

1. Never commit `.env` files
2. Use strong passwords for all services
3. Rotate API keys regularly
4. Monitor for unusual activity
5. Keep dependencies updated