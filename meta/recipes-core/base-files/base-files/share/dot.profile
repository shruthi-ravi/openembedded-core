# ~/.profile: executed by Bourne-compatible login shells.

if [ -f ~/.bashrc ]; then
  . ~/.bashrc
fi

# path set by /etc/profile
# export PATH

tty > /dev/null 2>&1 && mesg n
