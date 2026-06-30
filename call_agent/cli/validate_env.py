from call_agent.config import AzureOpenAIConfig


def main(load_dotenv_file: bool = True) -> None:
    config = AzureOpenAIConfig.from_env(load_dotenv_file=load_dotenv_file)

    print("Azure OpenAI config found.")
    print(f"Endpoint: {config.endpoint}")
    print(f"API version: {config.api_version}")
    print(f"Chat deployment: {config.chat_deployment}")
    print(f"Transcribe deployment: {config.transcribe_deployment}")
    print(f"TTS deployment: {config.tts_deployment}")
    print("API key: set")


if __name__ == "__main__":
    main()
