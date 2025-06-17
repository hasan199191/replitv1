# Render.com Deployment Guide

## 🚀 Step-by-Step Deployment

### 1. Prepare Your Repository

1. **Push to GitHub:**
   \`\`\`bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/yourusername/twitter-bot.git
   git push -u origin main
   \`\`\`

### 2. Create Render Account

1. Go to [render.com](https://render.com)
2. Sign up with your GitHub account
3. Connect your GitHub repository

### 3. Create New Web Service

1. Click "New +" button
2. Select "Web Service"
3. Connect your GitHub repository
4. Choose the repository with your Twitter bot

### 4. Configure Service Settings

**Basic Settings:**
- **Name:** `twitter-bot` (or your preferred name)
- **Region:** Oregon (recommended)
- **Branch:** `main`
- **Runtime:** Docker
- **Build Command:** Leave empty (Docker handles this)
- **Start Command:** Leave empty (Docker CMD handles this)

**Advanced Settings:**
- **Plan:** Starter ($7/month) - Free tier won't work due to Chrome requirements
- **Health Check Path:** `/health`
- **Auto-Deploy:** Yes

### 5. Set Environment Variables

Add these environment variables in Render dashboard:

\`\`\`
GEMINI_API_KEY=your_gemini_api_key_here
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_email_password
TWITTER_USERNAME=your_twitter_username
TWITTER_PASSWORD=your_twitter_password
IS_RENDER=true
PYTHONUNBUFFERED=1
\`\`\`

**⚠️ Important:** Keep these values secret and never commit them to your repository.

### 6. Deploy

1. Click "Create Web Service"
2. Render will automatically build and deploy your bot
3. Monitor the build logs for any errors

### 7. Monitor Your Bot

**Check Logs:**
- Go to your service dashboard
- Click on "Logs" tab
- Monitor for successful initialization and activity

**Health Check:**
- Your service should show "Live" status
- Health endpoint: `https://your-service-name.onrender.com/health`

## 🔧 Troubleshooting

### Common Issues:

1. **Build Fails:**
   - Check Dockerfile syntax
   - Ensure all files are committed to GitHub
   - Check build logs for specific errors

2. **Chrome/ChromeDriver Issues:**
   - Render uses Ubuntu, Chrome installation should work
   - Check logs for Chrome-related errors
   - Ensure headless mode is enabled

3. **Memory Issues:**
   - Upgrade to higher plan if needed
   - Monitor memory usage in logs

4. **Rate Limiting:**
   - Twitter may rate limit your bot
   - Check logs for rate limit errors
   - Adjust timing between actions if needed

### Log Monitoring:

\`\`\`bash
# Check if bot is running
curl https://your-service-name.onrender.com/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00",
  "service": "twitter-bot",
  "version": "1.0.0"
}
\`\`\`

## 📊 Performance Tips

1. **Monitor Resource Usage:**
   - Check CPU and memory usage in Render dashboard
   - Upgrade plan if consistently hitting limits

2. **Optimize Timing:**
   - Adjust sleep intervals between actions
   - Monitor for rate limit warnings

3. **Error Handling:**
   - Bot includes comprehensive error handling
   - Check logs regularly for any issues

## 🔄 Updates and Maintenance

1. **Code Updates:**
   - Push changes to GitHub
   - Render will auto-deploy if enabled

2. **Environment Variables:**
   - Update in Render dashboard
   - Restart service after changes

3. **Monitoring:**
   - Set up alerts in Render dashboard
   - Monitor bot activity through logs

## 💰 Cost Estimation

- **Starter Plan:** $7/month
- **Professional Plan:** $25/month (if you need more resources)
- **Additional costs:** None for basic usage

## 🛡️ Security Best Practices

1. **Never commit sensitive data to GitHub**
2. **Use strong passwords for Twitter account**
3. **Regularly rotate API keys**
4. **Monitor bot activity for unusual behavior**
5. **Keep dependencies updated**

## 📞 Support

If you encounter issues:
1. Check Render documentation
2. Review bot logs for error messages
3. Check Twitter API status
4. Verify all environment variables are set correctly
\`\`\`

Deployment için gerekli tüm dosyalar:
