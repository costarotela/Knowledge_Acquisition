# Getting Started

## Prerequisites

- Python 3.11 or higher
- Git
- OpenAI API key
- PostgreSQL (for vector storage)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/costarotela/Knowledge_Acquisition.git
cd Knowledge_Acquisition
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Quick Start

1. **Configure your OpenAI API key**:
   Edit `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your-api-key-here
   ```

2. **Initialize the database**:
   ```bash
   python scripts/init_db.py
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```

4. Open your browser and navigate to `http://localhost:8501`

## Basic Usage

1. **Add Knowledge Sources**:
   - Upload documents
   - Add URLs for scraping
   - Connect to data sources

2. **Process Knowledge**:
   - Trigger knowledge extraction
   - Monitor processing status
   - View extracted knowledge

3. **Query Knowledge**:
   - Use natural language queries
   - Explore knowledge graph
   - Export results

## Next Steps

- Read the [Configuration Guide](configuration.md) for detailed setup
- Check out the [Examples](examples.md) for common use cases
- Review the [API Documentation](../api/scrapers.md) for integration
- Join our [Community](https://github.com/costarotela/Knowledge_Acquisition/discussions)
