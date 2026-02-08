#!/data/data/com.termux/files/usr/bin/bash

cd ~/storage/shared/script/unlock-tool || exit 1

tmux new-session -d -s mibox

# Create layout: 4 panes
tmux split-window -h
tmux split-window -v
tmux select-pane -t 0
tmux split-window -v

# Run script in each pane
tmux send-keys -t 0 "python script.py" C-m
tmux send-keys -t 1 "python script.py" C-m
tmux send-keys -t 2 "python script.py" C-m
tmux send-keys -t 3 "python script.py" C-m

tmux attach-session -t mibox
