"""Analyse microstructure des marchés Kalshi météo (Phase B-2).

Mesure empiriquement, sur snapshots de markets, les biais structurels qu'on
peut exploiter SANS modèle météo amélioré :
- vig & écart à la sommation à 1 sur events mutuellement exclusifs ;
- spread bid/ask et sa dépendance à la position dans la distribution ;
- tail underpricing (les bins extrêmes paient plus que leur juste prix climato) ;
- concentration de l'open interest sur le bin modal.
"""
