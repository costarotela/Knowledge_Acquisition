"""
Extractor de conceptos y relaciones del contenido.
"""

from typing import List, Dict, Tuple, Set
import re
import logging
from collections import defaultdict
import spacy
from spacy.tokens import Doc, Span
from ..models.video_models import KnowledgeDomain

logger = logging.getLogger(__name__)

class ConceptExtractor:
    """Extrae conceptos y sus relaciones del contenido."""
    
    def __init__(self):
        """Inicializa el extractor de conceptos."""
        # Cargar modelo spaCy ligero para español/inglés
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.info("Descargando modelo spaCy...")
            spacy.cli.download("en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")
        
        # Patrones para identificar definiciones
        self.definition_patterns = [
            r"(?P<concept>[^,.:;]+)\s+(?:is|are)\s+(?:defined\s+as\s+)?(?P<definition>[^.;]+)[.;]?",
            r"(?P<concept>[^,.:;]+)\s+refers?\s+to\s+(?P<definition>[^.;]+)[.;]?",
            r"(?P<definition>[^.;]+)\s+is\s+called\s+(?P<concept>[^.;]+)[.;]?",
            r"(?P<concept>[^,.:;]+)\s+means?\s+(?P<definition>[^.;]+)[.;]?",
        ]
        
        # Patrones para relaciones
        self.relation_patterns = {
            "is_part_of": [
                r"(?P<source>[^,.;]+)\s+is\s+(?:a\s+)?part\s+of\s+(?P<target>[^.;]+)[.;]?",
                r"(?P<target>[^,.;]+)\s+contains?\s+(?P<source>[^.;]+)[.;]?",
                r"(?P<target>[^,.;]+)\s+consists?\s+of\s+(?P<source>[^.;]+)[.;]?",
                r"(?P<source>[^,.;]+)\s+belongs?\s+to\s+(?P<target>[^.;]+)[.;]?",
            ],
            "is_type_of": [
                r"(?P<source>[^,.;]+)\s+is\s+a\s+(?:type|kind|form)\s+of\s+(?P<target>[^.;]+)[.;]?",
                r"(?P<source>[^,.;]+)\s+is\s+an?\s+(?P<target>[^.;]+)[.;]?",
                r"(?P<source>[^,.;]+)\s+(?:can\s+be\s+)?classified\s+as\s+(?:a|an)?\s+(?P<target>[^.;]+)[.;]?",
            ],
            "affects": [
                r"(?P<source>[^,.;]+)\s+affects?\s+(?P<target>[^.;]+)[.;]?",
                r"(?P<source>[^,.;]+)\s+impacts?\s+(?P<target>[^.;]+)[.;]?",
                r"(?P<source>[^,.;]+)\s+influences?\s+(?P<target>[^.;]+)[.;]?",
                r"(?P<source>[^,.;]+)\s+(?:has|have)\s+an?\s+effect\s+on\s+(?P<target>[^.;]+)[.;]?",
            ],
            "requires": [
                r"(?P<source>[^,.;]+)\s+requires?\s+(?P<target>[^.;]+)[.;]?",
                r"(?P<source>[^,.;]+)\s+needs?\s+(?P<target>[^.;]+)[.;]?",
                r"(?P<target>[^,.;]+)\s+is\s+(?:necessary|required|essential)\s+for\s+(?P<source>[^.;]+)[.;]?",
                r"(?P<source>[^,.;]+)\s+depends?\s+on\s+(?P<target>[^.;]+)[.;]?",
            ],
            "similar_to": [
                r"(?P<source>[^,.;]+)\s+(?:is|are)\s+similar\s+to\s+(?P<target>[^.;]+)[.;]?",
                r"(?P<source>[^,.;]+)\s+(?:is|are)\s+like\s+(?P<target>[^.;]+)[.;]?",
                r"(?P<source>[^,.;]+)\s+resembles?\s+(?P<target>[^.;]+)[.;]?",
            ]
        }
        
        # Términos comunes que no deben ser conceptos
        self.stopwords = {
            "this", "that", "these", "those", "it", "they", "he", "she",
            "which", "who", "what", "where", "when", "why", "how"
        }
    
    def _clean_text(self, text: str) -> str:
        """
        Limpia y normaliza el texto.
        
        Args:
            text: Texto a limpiar
            
        Returns:
            Texto limpio y normalizado
        """
        # Eliminar saltos de línea y espacios múltiples
        text = re.sub(r'\s+', ' ', text)
        # Normalizar puntuación
        text = re.sub(r'\s*([.,;:])\s*', r'\1 ', text)
        # Eliminar espacios al inicio y final
        return text.strip()
    
    def _preprocess_text(self, text: str) -> Doc:
        """
        Preprocesa el texto usando spaCy.
        
        Args:
            text: Texto a procesar
            
        Returns:
            Documento spaCy procesado
        """
        text = self._clean_text(text)
        return self.nlp(text)
    
    def _extract_noun_phrases(self, doc: Doc) -> Dict[str, float]:
        """
        Extrae frases nominales del documento con puntuación.
        
        Args:
            doc: Documento spaCy
            
        Returns:
            Diccionario de frase nominal -> puntuación
        """
        noun_phrases = {}
        
        for chunk in doc.noun_chunks:
            # Limpiar y normalizar
            phrase = chunk.text.lower().strip()
            
            # Filtrar frases no deseadas
            if (2 <= len(phrase.split()) <= 5 and 
                not any(w in self.stopwords for w in phrase.split())):
                
                # Calcular puntuación basada en:
                # - Longitud de la frase (frases más largas suelen ser más específicas)
                # - Frecuencia en el documento
                # - Posición en la oración
                length_score = min(len(phrase.split()) / 5.0, 1.0)
                freq_score = sum(1 for sent in doc.sents if phrase in sent.text.lower()) / len(list(doc.sents))
                pos_score = 1.0 if chunk.start == 0 else 0.5  # Mayor peso si está al inicio
                
                score = (length_score + freq_score + pos_score) / 3.0
                noun_phrases[phrase] = score
        
        return noun_phrases
    
    def _extract_definitions(self, text: str) -> Dict[str, Dict]:
        """
        Extrae definiciones de conceptos usando patrones.
        
        Args:
            text: Texto a analizar
            
        Returns:
            Diccionario de concepto -> {definición, confianza}
        """
        definitions = {}
        text = self._clean_text(text)
        
        for pattern in self.definition_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                concept = match.group("concept").strip().lower()
                definition = match.group("definition").strip()
                
                if len(concept.split()) <= 5 and not any(w in self.stopwords for w in concept.split()):
                    # Calcular confianza basada en:
                    # - Longitud de la definición
                    # - Presencia de palabras clave
                    # - Patrón utilizado
                    def_length = len(definition.split())
                    length_score = min(def_length / 20.0, 1.0)  # Normalizar a max 20 palabras
                    
                    key_words = {"is", "means", "refers", "consists", "defined"}
                    kw_score = sum(1 for w in key_words if w in definition.lower()) / len(key_words)
                    
                    confidence = (length_score + kw_score) / 2.0
                    
                    # Actualizar solo si es mejor definición
                    if concept not in definitions or confidence > definitions[concept]["confidence"]:
                        definitions[concept] = {
                            "definition": definition,
                            "confidence": confidence
                        }
        
        return definitions
    
    def _extract_relations(self, text: str) -> Dict[str, List[Dict]]:
        """
        Extrae relaciones entre conceptos usando patrones.
        
        Args:
            text: Texto a analizar
            
        Returns:
            Diccionario de tipo_relación -> [{source, target, confidence}]
        """
        relations = defaultdict(list)
        text = self._clean_text(text)
        
        for rel_type, patterns in self.relation_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    source = match.group("source").strip().lower()
                    target = match.group("target").strip().lower()
                    
                    if (len(source.split()) <= 5 and len(target.split()) <= 5 and
                        not any(w in self.stopwords for w in source.split() + target.split())):
                        
                        # Calcular confianza
                        context_before = text[max(0, match.start() - 50):match.start()].strip()
                        context_after = text[match.end():min(len(text), match.end() + 50)].strip()
                        
                        # Factores de confianza:
                        # - Longitud de los conceptos
                        # - Contexto alrededor
                        # - Patrón utilizado
                        length_score = min((len(source.split()) + len(target.split())) / 10.0, 1.0)
                        context_score = 1.0 if any(w in context_before + context_after 
                                                for w in ["therefore", "because", "since", "as"]) else 0.5
                        
                        confidence = (length_score + context_score) / 2.0
                        
                        relations[rel_type].append({
                            "source": source,
                            "target": target,
                            "confidence": confidence
                        })
        
        return relations
    
    def _extract_domain_specific_concepts(self, text: str, domains: List[KnowledgeDomain]) -> Dict[str, Dict[str, float]]:
        """
        Extrae conceptos específicos de cada dominio con puntuación.
        
        Args:
            text: Texto a analizar
            domains: Lista de dominios detectados
            
        Returns:
            Diccionario de dominio -> {concepto: puntuación}
        """
        domain_concepts = defaultdict(dict)
        doc = self._preprocess_text(text)
        
        # Extraer todas las frases nominales con puntuación
        noun_phrases = self._extract_noun_phrases(doc)
        
        # Asignar conceptos a dominios basado en keywords y calcular relevancia
        for domain in domains:
            for concept, base_score in noun_phrases.items():
                # Calcular relevancia para el dominio
                keyword_matches = sum(1 for kw in domain.key_concepts 
                                   if kw.lower() in concept)
                domain_score = (keyword_matches / len(domain.key_concepts)) if domain.key_concepts else 0
                
                # Combinar puntuaciones
                final_score = (base_score + domain_score) / 2.0
                
                if domain_score > 0:  # Solo incluir si hay alguna relación con el dominio
                    domain_concepts[domain.name][concept] = final_score
        
        return domain_concepts
    
    def extract_knowledge_graph(self, text: str, domains: List[KnowledgeDomain]) -> Dict:
        """
        Extrae un grafo de conocimiento del texto.
        
        Args:
            text: Texto a analizar
            domains: Lista de dominios detectados
            
        Returns:
            Diccionario con el grafo de conocimiento
        """
        try:
            # 1. Extraer conceptos por dominio con puntuación
            domain_concepts = self._extract_domain_specific_concepts(text, domains)
            
            # 2. Extraer definiciones con confianza
            definitions = self._extract_definitions(text)
            
            # 3. Extraer relaciones con confianza
            relations = self._extract_relations(text)
            
            # 4. Construir grafo de conocimiento
            knowledge_graph = {
                "concepts": {
                    domain: [
                        {"term": concept, "relevance": score}
                        for concept, score in sorted(
                            concepts.items(), 
                            key=lambda x: x[1], 
                            reverse=True
                        )
                    ]
                    for domain, concepts in domain_concepts.items()
                },
                "definitions": [
                    {
                        "term": concept,
                        "definition": data["definition"],
                        "confidence": data["confidence"]
                    }
                    for concept, data in sorted(
                        definitions.items(),
                        key=lambda x: x[1]["confidence"],
                        reverse=True
                    )
                ],
                "relations": {
                    rel_type: sorted(
                        relations_list,
                        key=lambda x: x["confidence"],
                        reverse=True
                    )
                    for rel_type, relations_list in relations.items()
                }
            }
            
            return knowledge_graph
            
        except Exception as e:
            logger.error(f"Error al extraer grafo de conocimiento: {e}")
            return {
                "concepts": {},
                "definitions": [],
                "relations": {}
            }
