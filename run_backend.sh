#!/bin/bash
cd backend
uvicorn main:app --reload --port 8000
