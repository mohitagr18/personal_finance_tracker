🤖 AI Financial Data AnalystWelcome to the AI Financial Data Analyst, a Streamlit web application that transforms your PDF bank statements into an interactive financial dashboard. This app uses a powerful pipeline of cloud services and multi-agent AI systems to automate the entire process of data extraction, categorization, and analysis.This app uses Google's Document AI to read your PDFs, then unleashes a team of AutoGen agents powered by GPT-4o to answer your questions. It's a squad of financial robots ready to do your busywork, so you don't have to.✨ FeaturesSecure File Upload: Upload multiple PDF bank statements directly in the browser.Automated Data Extraction: Leverages Google Cloud's Document AI to accurately parse transaction details from complex PDF layouts.AI-Powered Categorization: An AutoGen agent intelligently categorizes each transaction into predefined categories like "Food & Dining," "Travel," etc.Interactive Q&A: Ask broad or specific questions in plain English and receive detailed answers, tables, and charts.Comprehensive Reporting: Generate full markdown reports with executive summaries, KPI tables, and visualizations for broad questions.On-the-Fly Charting: For specific questions, the AI analyst generates relevant charts (e.g., bar charts for top spend categories) to support its findings.Downloadable Reports: Download comprehensive analysis reports as clean, printable PDF files.Efficient Session Management: The heavy data processing (parsing and categorization) runs only once per session, ensuring subsequent questions are answered quickly.🛠️ Tech StackFrontend: StreamlitAI Agent Framework: Microsoft AutoGenLanguage Models: OpenAI GPT-4oPDF Data Extraction: Google Cloud Document AICore Libraries: Pandas, Matplotlib, SeabornPDF Generation: markdown-pdf📂 Project StructureThe project is organized into logical modules for clear separation of concerns:/
|-- statements/             # Temporarily stores uploaded user PDFs
|-- temp/                   # For intermediate files (e.g., data.csv) and run outputs
|-- agents/                 # AutoGen agent definitions and prompts
|   |-- prompts/
|   |   |-- categorizer_prompt.py
|   |   `-- data_analyzer_prompt.py
|   |-- categorizer_agent.py
|   |-- code_executor_agent.py
|   `-- data_analyzer_agent.py
|-- config/                 # Configuration files
|   `-- constants.py
|-- models/                 # AI model client initializers
|   `-- model_client.py
|-- services/               # Core data processing tasks
|   |-- categorizer_task.py
|   `-- parser.py
|-- teams/                  # AutoGen team definitions
|   `-- finance_team.py
|-- .env.example            # Example environment file
|-- .gitignore
|-- README.md               # This file
|-- requirements.txt        # Python dependencies
`-- streamlit_app.py        # The main application entry point
🚀 Setup and InstallationFollow these steps to run the application locally or in a cloud environment like GitHub Codespaces.1. Clone the Repositorygit clone <your-repository-url>
cd <your-repository-directory>
2. Set Up a Python EnvironmentIt is highly recommended to use a virtual environment.python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
3. Install DependenciesInstall all the required Python packages.pip install -r requirements.txt
4. Configure Environment VariablesYou will need to provide API keys and configuration details in an environment file.Create a .env file in the root of the project. You can copy the .env.example file to get started.Add your OpenAI API Key:OPENAI_API_KEY2="sk-..."
Set up Google Cloud Credentials:Create a service account in GCP with the "Document AI User" role and download the JSON key file.Copy the entire content of the JSON key file.Add it to your .env file like this:GCP_CREDENTIALS_JSON='''
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "...",
  ...
}
'''
Update Document AI Details (Optional): If your GCP project_id or processor_id are different from the ones in the code, add them to the .env file as well.▶️ Running the ApplicationOnce the setup is complete, run the Streamlit app from your terminal. Use the python -m prefix for best compatibility in virtual environments.python -m streamlit run streamlit_app.py
The application will open in your web browser.📝 How to Use the AppThe application follows a simple two-step process:Process Statements: Use the sidebar to upload one or more PDF bank statements. Click the "Process Uploaded Statements" button. The app will provide real-time status updates in the sidebar as it saves, parses, and categorizes your data. This step only needs to be run once per session.Ask a Question: Once processing is complete, the main area will unlock. You can now type any question about your finances into the text box and click "Analyze Data".For broad questions (e.g., "give me a full report"), the AI will generate a detailed markdown report with tables and charts.For specific questions (e.g., "what were my top 5 expenses in July?"), the AI will provide a direct answer and may generate a supporting chart.Enjoy your automated financial analysis!
