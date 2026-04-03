from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class ModelResponse:
    """
    Represents a single model response with its evaluation metrics.
    
    Attributes:
        quality (float): Quality score of the response (0.0 to 1.0).
        cost (float): Cost efficiency score of the response (0.0 to 1.0).
        latency (float): Latency performance score of the response (0.0 to 1.0).
        confidence (float): Confidence level of the response (0.0 to 1.0).
    """
    quality: float
    cost: float
    latency: float
    confidence: float


@dataclass
class ConsensusResult:
    """
    Represents the consensus result from evaluating multiple model responses.
    
    Attributes:
        weighted_score (float): The calculated weighted consensus score.
        consensus_level (str): The consensus level ('full', 'partial', or 'none').
        num_responses (int): Number of responses evaluated.
    """
    weighted_score: float
    consensus_level: str
    num_responses: int


class WeightedScoreConsensus:
    """
    A class to calculate weighted consensus scores from multiple model responses.
    
    Uses predefined weights for different metrics and determines consensus levels
    based on threshold values.
    """
    
    # Predefined weights for each metric
    WEIGHTS = {
        'quality': 0.40,
        'cost': 0.30,
        'latency': 0.20,
        'confidence': 0.10
    }
    
    # Thresholds for consensus levels
    FULL_THRESHOLD = 0.75
    PARTIAL_THRESHOLD = 0.50
    
    def evaluate(self, responses: List[ModelResponse]) -> ConsensusResult:
        """
        Evaluate a list of model responses and return a consensus result.
        
        Args:
            responses: List of ModelResponse objects to evaluate.
            
        Returns:
            ConsensusResult containing the weighted score, consensus level, 
            and number of responses.
            
        Raises:
            ValueError: If responses list is empty.
        """
        if not responses:
            raise ValueError("Responses list cannot be empty")
        
        total_weighted_score = 0.0
        
        for response in responses:
            total_weighted_score += self.calculate_weighted_score(response)
        
        average_score = total_weighted_score / len(responses)
        
        if average_score >= self.FULL_THRESHOLD:
            consensus_level = "full"
        elif average_score >= self.PARTIAL_THRESHOLD:
            consensus_level = "partial"
        else:
            consensus_level = "none"
        
        return ConsensusResult(
            weighted_score=average_score,
            consensus_level=consensus_level,
            num_responses=len(responses)
        )
    
    def calculate_weighted_score(self, response: ModelResponse) -> float:
        """
        Calculate the weighted score for a single model response.
        
        Args:
            response: ModelResponse object containing the metrics.
            
        Returns:
            The weighted score as a float between 0.0 and 1.0.
        """
        return (
            response.quality * self.WEIGHTS['quality'] +
            response.cost * self.WEIGHTS['cost'] +
            response.latency * self.WEIGHTS['latency'] +
            response.confidence * self.WEIGHTS['confidence']
        )