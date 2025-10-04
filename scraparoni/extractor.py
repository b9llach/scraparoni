"""
Scraparoni - Intelligent LLM-based Data Extraction
Transform raw HTML into structured data using local LLMs
"""

import json
import re
from typing import Type, Optional, Dict, Any
from pydantic import BaseModel

# Import transformers at module level for consistency
# This causes ~5-10s delay on import, but makes subsequent operations faster
from transformers import AutoModelForCausalLM, AutoTokenizer


class ScraparoniExtractor:
    """
    LLM-powered data extraction engine
    Weaves structured data from the web using local language models
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-7B-Instruct-1M",
        device_map: str = "auto",
        dtype: str = "auto",
        verbose: bool = False,
    ):
        """
        Initialize ScraparoniExtractor with a local LLM

        Args:
            model_name: HuggingFace model identifier
            device_map: Device mapping strategy
            torch_dtype: Torch dtype for model
            verbose: Show detailed loading progress
        """
        if verbose:
            print(f"🕸️  Loading Weaver with {model_name}...")

        import sys

        # Load tokenizer first (fast)
        if verbose:
            print(f"   📖 Loading tokenizer...", end="", flush=True)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        if verbose:
            print(f" ✓")

        # Load model (slow - this is where the delay is)
        if verbose:
            print(f"   🧠 Loading model config and initializing...", end="", flush=True)
            sys.stdout.flush()

        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            dtype=dtype,
            device_map=device_map
        )

        if verbose:
            print(f"\n✓ ScraparoniExtractor ready!")

    def extract(
        self,
        html_content: str,
        schema: Type[BaseModel],
        instructions: Optional[str] = None,
        max_length: int = 15000,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        smart_chunking: bool = True,
    ) -> BaseModel:
        """
        Extract structured data from HTML using LLM with smart chunking with ScraparoniExtractor   

        Args:
            html_content: Raw HTML content to extract from
            schema: Pydantic model defining extraction schema
            instructions: Additional extraction instructions
            max_length: Max HTML characters per chunk (default: 15k for speed)
            temperature: LLM temperature (lower = more deterministic)
            max_tokens: Max tokens to generate
            smart_chunking: Use intelligent chunking for large HTML (default: True)

        Returns:
            Validated Pydantic model instance

        Raises:
            ValueError: If JSON extraction or validation fails
        """
        # If HTML is small enough, extract directly
        if len(html_content) <= max_length or not smart_chunking:
            return self._extract_single(
                html_content[:max_length],
                schema,
                instructions,
                temperature,
                max_tokens
            )

        # Large HTML - use smart chunking
        return self._extract_chunked(
            html_content,
            schema,
            instructions,
            max_length,
            temperature,
            max_tokens
        )

    def _extract_single(
        self,
        html_content: str,
        schema: Type[BaseModel],
        instructions: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> BaseModel:
        """Extract from a single HTML chunk"""
        schema_json = schema.model_json_schema()
        schema_description = json.dumps(schema_json, indent=2)

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            html_content,
            schema_description,
            instructions
        )

        response = self._generate(
            system_prompt,
            user_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )

        json_data = self._extract_json_from_tags(response)
        return schema.model_validate(json_data)

    def _extract_chunked(
        self,
        html_content: str,
        schema: Type[BaseModel],
        instructions: Optional[str],
        chunk_size: int,
        temperature: float,
        max_tokens: int,
    ) -> BaseModel:
        """
        Extract from large HTML by splitting into chunks and finding relevant sections
        Now tries ALL high-relevance chunks instead of stopping at first success
        """
        # Get field descriptions to search for relevant sections
        schema_json = schema.model_json_schema()
        field_keywords = self._extract_keywords_from_schema(schema_json)

        # Split HTML into overlapping chunks
        chunks = self._create_chunks(html_content, chunk_size, overlap=1000)

        # Score each chunk by keyword relevance
        scored_chunks = []
        for i, chunk in enumerate(chunks):
            score = self._score_chunk_relevance(chunk, field_keywords)
            scored_chunks.append((score, i, chunk))

        # Sort by relevance
        scored_chunks.sort(reverse=True, key=lambda x: x[0])

        # Try extraction from chunks with relevance > 0.4 (instead of just top 3)
        # This ensures we don't miss data spread across multiple sections
        # while avoiding low-quality chunks
        best_result = None
        best_data_count = 0

        for score, idx, chunk in scored_chunks:
            # Skip chunks with low relevance
            if score < 0.4:
                break

            try:
                result = self._extract_single(
                    chunk,
                    schema,
                    instructions,
                    temperature,
                    max_tokens
                )

                # Count non-empty data items
                data = result.model_dump()
                data_count = self._count_data_items(data)

                # Keep track of result with most data
                if data_count > best_data_count:
                    best_data_count = data_count
                    best_result = result

            except Exception as e:
                continue

        # Return the result with the most data found
        if best_result and best_data_count > 0:
            return best_result

        # If all chunks failed, try the first chunk as fallback
        return self._extract_single(
            scored_chunks[0][2],
            schema,
            instructions,
            temperature,
            max_tokens
        )

    def _count_data_items(self, data: dict) -> int:
        """Count number of non-empty data items in extraction result"""
        count = 0
        for key, value in data.items():
            if isinstance(value, list):
                count += len([item for item in value if item and item != {} and item != []])
            elif value and value != "" and value != {} and value != []:
                count += 1
        return count

    def _extract_keywords_from_schema(self, schema_json: dict) -> list[str]:
        """Extract keywords from schema field descriptions"""
        keywords = []
        properties = schema_json.get("properties", {})

        for field_name, field_info in properties.items():
            # Add field name
            keywords.append(field_name.lower())

            # Add words from description
            description = field_info.get("description", "")
            words = re.findall(r'\w+', description.lower())
            keywords.extend(words)

        return list(set(keywords))

    def _create_chunks(self, text: str, chunk_size: int, overlap: int) -> list[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap

        return chunks

    def _score_chunk_relevance(self, chunk: str, keywords: list[str]) -> float:
        """Score chunk by keyword density"""
        chunk_lower = chunk.lower()
        matches = sum(1 for keyword in keywords if keyword in chunk_lower)
        return matches / len(keywords) if keywords else 0

    def extract_batch(
        self,
        html_contents: list[str],
        schema: Type[BaseModel],
        instructions: Optional[str] = None,
        **kwargs
    ) -> list[BaseModel]:
        """
        Extract data from multiple HTML documents

        Args:
            html_contents: List of HTML strings
            schema: Pydantic schema
            instructions: Extraction instructions
            **kwargs: Additional extract() arguments

        Returns:
            List of validated Pydantic instances
        """
        results = []
        for i, html in enumerate(html_contents):
            result = self.extract(html, schema, instructions, **kwargs)
            results.append(result)
        return results

    def _build_system_prompt(self) -> str:
        """Build system prompt for extraction"""
        return (
            "You are Silk, an expert web scraping AI. Your task is to extract structured data "
            "from HTML content with precision and accuracy. Follow the schema exactly. "
            "Return ONLY valid JSON wrapped in <json></json> tags. Be thorough but concise. "
            "If a field is not found, use null for optional fields or your best inference for required fields."
        )

    def _build_user_prompt(
        self,
        html: str,
        schema: str,
        instructions: Optional[str]
    ) -> str:
        """Build user prompt with HTML and schema"""
        prompt = f"""Extract structured data from the HTML below according to this schema.

SCHEMA:
{schema}

{f'INSTRUCTIONS: {instructions}' if instructions else ''}

HTML CONTENT:
{html}

Extract the data and return it as valid JSON wrapped in <json></json> tags."""
        return prompt

    def _generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        """
        Generate LLM response

        Args:
            system_prompt: System message
            user_prompt: User message
            temperature: Sampling temperature
            max_tokens: Max tokens to generate

        Returns:
            Generated text
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Apply chat template
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        # Tokenize
        model_inputs = self.tokenizer(
            [text],
            return_tensors="pt"
        ).to(self.model.device)

        # Generate
        generated_ids = self.model.generate(
            **model_inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_p=0.9,
            do_sample=temperature > 0,
        )

        # Decode only new tokens
        generated_ids = [
            output_ids[len(input_ids):]
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        response = self.tokenizer.batch_decode(
            generated_ids,
            skip_special_tokens=True
        )[0]

        return response

    def _extract_json_from_tags(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON content from <json></json> tags

        Args:
            text: LLM response text

        Returns:
            Parsed JSON dict

        Raises:
            ValueError: If no JSON tags found or invalid JSON
        """
        # Try to find JSON in tags
        pattern = r'<json>(.*?)</json>'
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

        if not match:
            # Fallback: try to find any JSON object
            json_pattern = r'\{.*\}'
            match = re.search(json_pattern, text, re.DOTALL)
            if not match:
                raise ValueError(
                    f"No <json> tags or valid JSON found in LLM response.\n"
                    f"Response: {text[:500]}..."
                )
            json_str = match.group(0)
        else:
            json_str = match.group(1).strip()

        # Parse JSON
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in LLM response: {str(e)}\n"
                f"JSON string: {json_str[:500]}..."
            )

    def custom_prompt(
        self,
        html_content: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        max_html_length: int = 15000,
    ) -> str:
        """
        Run custom extraction prompt without schema validation

        Args:
            html_content: HTML to analyze
            prompt: Custom extraction prompt
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            max_html_length: Max HTML chars to send (default: 15k)

        Returns:
            Raw LLM response
        """
        system_prompt = "You are Silk, an expert web scraping and analysis AI."

        user_prompt = f"""{prompt}

HTML CONTENT:
{html_content[:max_html_length]}"""

        return self._generate(
            system_prompt,
            user_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
