import threading

class Menu:
    def __init__(self, effects, effect_chain, looper, on_quit_callback):
        self.effects = effects
        self.effect_chain = effect_chain
        self.current_effect_idx = 0
        self.looper = looper
        self.running = True
        self.on_quit = on_quit_callback
        self.chain_mode = False

    def get_current_effect (self):
        if self.chain_mode:
            return self.effect_chain
        return self.effects[self.current_effect_idx]

    def display_menu(self):
        print("PyPiPedals")
        print("----------")

        print(f"\n[LOOPER: {self.looper.get_status()}]")
        if not self.chain_mode:
            print('\n[SINGLE EFFECT MODE]')
            print('\nEffects:')
            for i, effect in enumerate(self.effects, 1):
                marker = "->" if i-1 == self.current_effect_idx else " "
                print(f"    {marker} {i}. {effect.name}")
            print("\nCommands:")
            print(" 1-9 : select effect")
            print(" c   : switch to chain mode")
        else:
            print("\n[Chain mode - Multiple effects]")
            print("\nEffect Chain:")
            print(self.effect_chain.get_status_display())
            print(" 1-9 : Toggle effect on/off")
            print(" s   : Switch to single effect mode")
            print(" r   : Reset All effects")
        


        print("\nLooper Controls:")
        print("  L    : Start recording loop")
        print("  l    : Stop recording / Toggle playback")
        print("  x    : Clear loop")
        print(" Q   : quit")
        print("----------")

    def run(self):
        self.display_menu()

        while self.running:
            choice = input("> ").strip()
            
            if choice.isdigit():
                idx = int(choice) - 1

                if not self.chain_mode:
                    if 0 <= idx < len(self.effects):
                        self.current_effect_idx = idx
                        self.display_menu()
                        print(f"\n {self.effects[idx].name} enabled")
                    else:
                        print("Invalid effect number")
                else:
                    if self.effect_chain.toggle_effect(idx):
                        self.display_menu()
                        status = "ON" if self.effect_chain.is_active(idx) else "OFF"
                        print(f"\n {self.effect_chain.effects[idx].name} toggled {status}")
                    else:
                        print("invalid effect number")
            elif choice == "c" and not self.chain_mode:
                self.chain_mode = True
                self.display_menu()
                print("\n switched to chain mode")
            elif choice == "s" and self.chain_mode:
                self.chain_mode = False
                self.display_menu()
                print("\n Switched to single effect mode")
            elif choice == "r" and self.chain_mode:
                self.effect_chain.reset()
                print("\n all effects reset")
                # Looper controls
            # Looper controls - SPACEBAR (empty string = just pressing Enter)
            elif choice == "":
                # Empty input = spacebar/enter pressed
                if not self.looper.is_recording and self.looper.loop_length == 0:
                    # Start recording if no loop exists
                    msg = self.looper.start_recording()
                    print(f"\n♪ {msg}")
                elif self.looper.is_recording:
                    # Stop recording and start playback
                    msg = self.looper.stop_recording()
                    self.display_menu()
                    print(f"\n♪ {msg}")
                else:
                    # Toggle playback if loop exists
                    msg = self.looper.toggle_playback()
                    print(f"\n♪ {msg}")
            elif choice == "x":
                msg = self.looper.clear_loop()
                self.display_menu()
                print(f"\n♪ {msg}")
            elif choice == "q":
                print("exiting...")
                self.running = False
                self.on_quit()
                break
            else:
                print("unknown command")
    def start_thread(self):
        threading.Thread(target=self.run, daemon=True).start()