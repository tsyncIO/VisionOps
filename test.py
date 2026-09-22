import asyncio
from httpx import AsyncClient

async def test():
    async with AsyncClient() as client:
        # Create a dummy PDF
        with open("test.pdf", "wb") as f:
            f.write(b"%PDF-1.4\n%Fake PDF content for testing\n")
            
        # Upload
        with open("test.pdf", "rb") as f:
            res = await client.post("http://localhost:8001/api/documents", files={"file": f})
        print(res.json())
        doc_id = res.json()["document_id"]
        
        # Start run
        res = await client.post("http://localhost:8001/api/runs", json={"document_id": doc_id, "skill": "technical_document_to_diagram"})
        print(res.json())
        run_id = res.json()["run_id"]
        
        # Poll state
        await asyncio.sleep(5)
        res = await client.get(f"http://localhost:8001/api/runs/{run_id}")
        print(res.json())

asyncio.run(test())
