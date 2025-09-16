# This bot is a fresh prototype
And as such is not yet ready with teh features i would like to have like
- docker & docker compose files
- setup guide
- tracking of various metrics / export to prometheus
- example dashboard

# Why this bot exists?
I got teh idea to monitor my discord server for voice join times and tarck some fun metrics like
- Time suers spend in voice chats
- Total time someone was in a voice chat
- Maybe even voci chat distribution if i get facny with it

The goal was to make a heatmap / stats later in grafana -> this could inform later desicions on when
to host events like Dungeons and Dragons Games / Gaming evenings - since (in theory) we should a pretty good pattern insight
An i just think thats freaking cool - don't you? :D

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
With enough data, we should see clear patterns about when people are most active—and that’s just freaking cool, don’t you think? :D
