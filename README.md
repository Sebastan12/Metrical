# Metrical — Discord metrics exporter (prototype)

> A tiny Prometheus exporter bot for Discord, built for homelabs and Grafana dashboards.

## Status
This bot is a **fresh prototype**. It’s still missing:
- Dockerfile & docker-compose setup
- Setup / installation guide
- Tracking of multiple metrics + Prometheus export
- Example Grafana dashboard

## Why this bot exists
I wanted to monitor my Discord server’s voice activity and track some fun metrics:
- Time users spend in voice channels (per user)
- Total time **anyone** was in voice (union time)
- Voice activity distribution across days/hours (heatmap), if I get fancy

## Goal
Build heatmaps and stats in Grafana to help decide when to host events (e.g., Dungeons & Dragons sessions or gaming nights). 
With enough data, we should see clear patterns about when people are most active(and probably most likely to participate)—and that’s just freaking cool, don’t you think? :D
