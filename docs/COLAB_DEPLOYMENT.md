# 🦅 How to Deploy Ouroboros on Google Colab

Since you don't have a local GPU, we will run the AI "Brain" on Google Colab (Free Tier T4 GPU) and connect it to your local machine.

## Step 1: Upload the Notebook
1.  Open [Google Colab](https://colab.research.google.com/).
2.  Click **Upload** and select the file: `g:\Just a Idea\ouroboros_colab_server.ipynb`
    *   *(You can find this file in your project folder)*.

## Step 2: Configure Runtime
1.  In the Colab menu, click **Runtime** > **Change runtime type**.
2.  Set **Hardware accelerator** to **T4 GPU** (or better if available).
3.  Click **Save**.

## Step 3: Run the Server
1.  Click **Runtime** > **Run all** (or press `Ctrl+F9`).
2.  **Ngrok Setup**: You will be asked for an `ngrok` token.
    *   Go to [dashboard.ngrok.com](https://dashboard.ngrok.com/get-started/your-authtoken).
    *   Copy your Authtoken.
    *   Paste it in the Colab input box and press Enter.
3.  **Hugging Face Login**: You will be asked for a Hugging Face token.
    *   Paste your Write-enabled token and press Enter.

## Step 4: Connect Locally
1.  Scroll to the bottom of the Colab output.
2.  Look for the line: `🔥 SERVER RUNNING! 🔥`
3.  Copy the URL (e.g., `https://12ab-34-56.ngrok-free.app`).
4.  Open your local `.env` file (`g:\Just a Idea\.env`).
5.  Paste the URL:
    ```ini
    COLAB_API_URL=https://12ab-34-56.ngrok-free.app
    ```

## Step 5: You're Ready!
You can now run Ouroboros commands locally, and the heavy lifting will happen on Colab.
