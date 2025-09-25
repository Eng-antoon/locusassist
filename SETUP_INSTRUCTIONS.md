# Locus Assistant - Setup Instructions

## Google AI Integration Setup

To enable GRN validation with Google AI Studio, you need to set up your API key:

### 1. Get Google AI Studio API Key

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the API key

### 2. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and replace `your_google_ai_api_key_here` with your actual API key:
   ```
   GOOGLE_AI_API_KEY=your_actual_api_key_here
   ```

### 3. Restart the Application

After configuring the environment variables, restart the application:

```bash
source venv/bin/activate
python app.py
```

## Features

Once configured, you can:

- **Individual Order Validation**: Click the "Validate GRN" button on any order card in the dashboard or in the order detail view
- **Batch Validation**: Click "Validate All Orders" to validate all orders on the current date
- **View Results**: Green alerts show successful validations, red alerts show discrepancies with detailed explanations

## Validation Process

The system will:

1. Fetch the delivery document (GRN) image from the Locus API
2. Send the image to Google AI Studio (Gemini 2.5) for analysis
3. Extract item names, quantities, and other details from the document
4. Compare the extracted data with the order data from Locus
5. Report any discrepancies or confirm if everything matches

## Troubleshooting

- **"API key not configured"**: Make sure you've set the `GOOGLE_AI_API_KEY` in your `.env` file
- **"Failed to fetch image"**: The delivery document link might be invalid or the image might not be accessible
- **Rate limiting**: The batch validation includes delays between requests to respect API limits