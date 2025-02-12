# Scrapers API Reference

## Overview

The Scrapers API provides interfaces for extracting content from various sources including web pages, PDFs, and structured data sources.

## Web Scraper

### WebScraper Class

```python
class WebScraper:
    def __init__(self, config: ScraperConfig = None):
        """
        Initialize web scraper with optional configuration.
        
        Args:
            config (ScraperConfig): Configuration for the scraper
        """
        pass

    async def scrape_url(self, url: str) -> ScrapedContent:
        """
        Scrape content from a single URL.
        
        Args:
            url (str): URL to scrape
            
        Returns:
            ScrapedContent: Extracted content and metadata
        """
        pass

    async def scrape_urls(self, urls: List[str]) -> List[ScrapedContent]:
        """
        Scrape content from multiple URLs in parallel.
        
        Args:
            urls (List[str]): List of URLs to scrape
            
        Returns:
            List[ScrapedContent]: List of extracted contents
        """
        pass
```

### ScraperConfig Class

```python
@dataclass
class ScraperConfig:
    max_depth: int = 3
    respect_robots_txt: bool = True
    request_delay: float = 1.0
    timeout: int = 30
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
```

### ScrapedContent Class

```python
@dataclass
class ScrapedContent:
    url: str
    title: str
    text: str
    html: str
    metadata: Dict[str, Any]
    timestamp: datetime
    status: ScrapingStatus
```

## PDF Scraper

### PDFScraper Class

```python
class PDFScraper:
    def __init__(self, config: PDFConfig = None):
        """
        Initialize PDF scraper with optional configuration.
        
        Args:
            config (PDFConfig): Configuration for PDF processing
        """
        pass

    def extract_text(self, file_path: str) -> PDFContent:
        """
        Extract text content from a PDF file.
        
        Args:
            file_path (str): Path to PDF file
            
        Returns:
            PDFContent: Extracted content and metadata
        """
        pass

    def extract_tables(self, file_path: str) -> List[Table]:
        """
        Extract tables from a PDF file.
        
        Args:
            file_path (str): Path to PDF file
            
        Returns:
            List[Table]: List of extracted tables
        """
        pass
```

## Data Source Scraper

### DataSourceScraper Class

```python
class DataSourceScraper:
    def __init__(self, connection_string: str):
        """
        Initialize data source scraper.
        
        Args:
            connection_string (str): Database connection string
        """
        pass

    async def extract_data(self, query: str) -> DataFrame:
        """
        Extract data using SQL query.
        
        Args:
            query (str): SQL query to execute
            
        Returns:
            DataFrame: Extracted data
        """
        pass

    async def extract_schema(self) -> Dict[str, Any]:
        """
        Extract database schema information.
        
        Returns:
            Dict[str, Any]: Database schema
        """
        pass
```

## Utility Functions

```python
def validate_url(url: str) -> bool:
    """
    Validate URL format and accessibility.
    
    Args:
        url (str): URL to validate
        
    Returns:
        bool: True if valid and accessible
    """
    pass

def clean_text(text: str) -> str:
    """
    Clean and normalize extracted text.
    
    Args:
        text (str): Text to clean
        
    Returns:
        str: Cleaned text
    """
    pass

def extract_metadata(content: Any) -> Dict[str, Any]:
    """
    Extract metadata from content.
    
    Args:
        content (Any): Content to analyze
        
    Returns:
        Dict[str, Any]: Extracted metadata
    """
    pass
```

## Error Handling

```python
class ScraperError(Exception):
    """Base class for scraper exceptions."""
    pass

class URLError(ScraperError):
    """Raised when URL is invalid or inaccessible."""
    pass

class PDFError(ScraperError):
    """Raised when PDF processing fails."""
    pass

class DataSourceError(ScraperError):
    """Raised when data source access fails."""
    pass
```

## Usage Examples

```python
# Web scraping example
scraper = WebScraper(ScraperConfig(max_depth=2))
content = await scraper.scrape_url("https://example.com")

# PDF processing example
pdf_scraper = PDFScraper()
pdf_content = pdf_scraper.extract_text("document.pdf")

# Data source example
db_scraper = DataSourceScraper("postgresql://localhost/db")
data = await db_scraper.extract_data("SELECT * FROM table")
```
