#!/usr/bin/env python
import requests
import json
import argparse

def get_truncated_embeddings(text, model="snowflake-arctic-embed2:568m", output_dim=384):
    """
    Gets truncated embeddings for a given text using the Ollama API with MRL.

    Args:
        text (str): The text to embed.
        model (str): The Ollama model with MRL support (default: snowflake-arctic-embed2:568m).
        output_dim (int): The desired output dimensionality for the truncated embedding (default: 384).

    Returns:
        list: A list of floats representing the truncated embedding vector.
    """
    url = "http://localhost:11434/api/embed"
    payload = {
        "model": model,
        "input": text,
        "options": {
            "num_predict": output_dim # Specify the truncation dimension
        }
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        result = response.json()
        return result["embeddings"]
    except requests.exceptions.RequestException as e:
        print(f"Error getting embeddings from Ollama: {e}")
        return None

def process_file_and_get_truncated_embeddings(filename, output_dim=384, ollama_model="snowflake-arctic-embed2:568m"):
    """
    Reads a file, gets truncated embeddings from Ollama for each line, and returns a list of embeddings.

    Args:
        filename (str): The path to the text file to encode.
        output_dim (int): The desired output dimensionality for the truncated embeddings (default: 384).
        ollama_model (str): The Ollama model with MRL support (default: snowflake-arctic-embed2:568m).

    Returns:
        list: A list of truncated embeddings (or None if an error occurred).
    """
    truncated_embeddings = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                # Get truncated embeddings for each line
                print("X")
                embedding = get_truncated_embeddings(line.strip(), model=ollama_model, output_dim=output_dim)
                if embedding:
                    truncated_embeddings.append(embedding)
                else:
                    print(f"Warning: Could not get embedding for line: '{line.strip()}'")

    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return None
    except Exception as e:
        print(f"Error reading file or getting embeddings: {e}")
        return None

    if not truncated_embeddings:
        print("No valid embeddings were generated. Check the file content or Ollama server.")
        return None

    return truncated_embeddings

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Encode a file using Ollama with MRL and get truncated embeddings.")
    parser.add_argument("filename", type=str, help="The path to the text file to encode.")
    parser.add_argument("--output_dim", type=int, default=384, help="The desired output dimensionality for the truncated embeddings (default: 384).")
    parser.add_argument("--ollama_model", type=str, default="snowflake-arctic-embed2:568m", help="The Ollama model with MRL support (default: snowflake-arctic-embed2:568m).")
    args = parser.parse_args()

    truncated_embeddings = process_file_and_get_truncated_embeddings(args.filename, args.output_dim, args.ollama_model)

    if truncated_embeddings is not None:
        print(f"Successfully generated {len(truncated_embeddings)} truncated embeddings.")
        # You can now use the 'truncated_embeddings' list (which contains 384-dimensional vectors)
        # for storing in a vector database, performing similarity search, etc.
        # Example: print the first truncated embedding
        print("First truncated embedding:")
        print(truncated_embeddings[0]) # print the first truncated embedding
