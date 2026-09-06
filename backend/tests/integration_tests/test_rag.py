from lad.models.db import DocumentChunk


def test_document_chunk_cosine_similarity_returns_the_closer_vector(db_session):
    dim = 768

    close_vector = [1.0, 0.0] + [0.0] * (dim - 2)
    far_vector = [0.0, 1.0] + [0.0] * (dim - 2)
    query_vector = [0.9, 0.1] + [0.0] * (dim - 2)

    db_session.add_all(
        [
            DocumentChunk(
                source_path="a.py",
                chunk_index=0,
                content="def foo(): pass",
                embedding=close_vector,
            ),
            DocumentChunk(
                source_path="b.py",
                chunk_index=0,
                content="def bar(): pass",
                embedding=far_vector,
            ),
        ]
    )
    db_session.flush()

    results = (
        db_session.query(DocumentChunk)
        .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
        .limit(1)
        .all()
    )

    assert results[0].source_path == "a.py"
