from typing import Any, Dict, List, Optional

from core import get_conn


class FaqService:
    """FAQ data access helpers."""

    def ensure_table(self) -> None:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS faq (
                  faq_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  question VARCHAR(255) NOT NULL,
                  answer MEDIUMTEXT NOT NULL,
                  category VARCHAR(50) NULL,
                  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  is_visible TINYINT(1) NOT NULL DEFAULT 1
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

    def list_faq(self, query: Optional[str], category: Optional[str], limit: int) -> Dict[str, Any]:
        self.ensure_table()
        clauses = ["is_visible=1"]
        params: List[Any] = []
        if query:
            clauses.append("(question LIKE %s OR answer LIKE %s OR category LIKE %s)")
            like = f"%{query}%"
            params.extend([like, like, like])
        if category:
            clauses.append("category = %s")
            params.append(category)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
          SELECT faq_id, question, answer, category, created_at, updated_at, is_visible
          FROM faq
          {where}
          ORDER BY created_at DESC
          LIMIT %s
        """
        params.append(int(limit))
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall() or []
        return {"count": len(rows), "items": rows}

    def list_categories(self) -> Dict[str, Any]:
        self.ensure_table()
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT category
                FROM faq
                WHERE is_visible=1 AND category IS NOT NULL AND category <> ''
                ORDER BY category
                """
            )
            rows = cur.fetchall() or []
        return {"items": [r.get("category") for r in rows if r.get("category") is not None]}


faq_service = FaqService()
