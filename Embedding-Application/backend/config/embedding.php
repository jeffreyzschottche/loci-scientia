<?php

return [
    /*
    |--------------------------------------------------------------------------
    | Embedding defaults
    |--------------------------------------------------------------------------
    |
    | Central place to describe how we slice and describe chunks for the
    | embedding platform. Defaults align with the FastEmbed model that runs
    | in the root project (mpnet multilingual, 768 dims).
    |
    */

    'model' => env('EMBEDDING_MODEL', env('FASTEMBED_MODEL', 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2')),
    'vector_dimension' => (int) env('EMBEDDING_VECTOR_DIMENSION', 768),
    'chunk_tokens' => (int) env('EMBEDDING_CHUNK_TOKENS', 150),
    'chunk_overlap_tokens' => (int) env('EMBEDDING_CHUNK_OVERLAP_TOKENS', 80),
    'tokens_per_word' => (float) env('EMBEDDING_TOKENS_PER_WORD', 1.3),
];
