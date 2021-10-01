# Import libraries
import RPi.GPIO as GPIO
import random
import ES2EEPROMUtils
import os
import time

# some global variables that need to change as we run the program
end_of_game = False
guess = 0
guesses = 0
value = 0
play = False

# DEFINE THE PINS USED HERE
LED_value = [11, 13, 15]
LED_accuracy = 32
btn_submit = 16
btn_increase = 18
buzzer = 33
eeprom = ES2EEPROMUtils.ES2EEPROM()


# Print the game banner
def welcome():
    os.system('clear')
    print("  _   _                 _                  _____ _            __  __ _")
    print("| \ | |               | |                / ____| |          / _|/ _| |")
    print("|  \| |_   _ _ __ ___ | |__   ___ _ __  | (___ | |__  _   _| |_| |_| | ___ ")
    print("| . ` | | | | '_ ` _ \| '_ \ / _ \ '__|  \___ \| '_ \| | | |  _|  _| |/ _ \\")
    print("| |\  | |_| | | | | | | |_) |  __/ |     ____) | | | | |_| | | | | | |  __/")
    print("|_| \_|\__,_|_| |_| |_|_.__/ \___|_|    |_____/|_| |_|\__,_|_| |_| |_|\___|")
    print("")
    print("Guess the number and immortalise your name in the High Score Hall of Fame!")


# Print the game menu
def menu():
    global end_of_game
    global value
    global play

    play = False
    option = input("Select an option:   H - View High Scores     P - Play Game       Q - Quit\n")
    option = option.upper()
    if option == "H":
        os.system('clear')
        print("HIGH SCORES!!")
        s_count, ss = fetch_scores()
        display_scores(s_count, ss)
        menu()

    elif option == "P":
        os.system('clear')
        end_of_game = False
        play = True
        print("Starting a new round!")
        print("Use the buttons on the Pi to make and submit your guess!")
        print("Press and hold the guess button to cancel your game")
        value = generate_number()
        while not end_of_game:
            pass

    elif option == "Q":
        print("Come back soon!")
        exit()
    else:
        print("Invalid option. Please select a valid one!")


def display_scores(count, raw_data):
    # print the scores to the screen in the expected format
    print("There are {} scores. Here are the top 3!".format(count))
    # print out the scores in the required format
    for i in range(0,3):
        print((i+1),"- {} took {} guesses".format(raw_data[i][0]+raw_data[i][1]+raw_data[i][2],str(raw_data[i][3])))
    pass


# Setup Pins
def setup():
    # Setup board mode
    GPIO.setmode(GPIO.BOARD)
    # Setup regular GPIO
    GPIO.setup(LED_value[0], GPIO.OUT)
    GPIO.setup(LED_value[1], GPIO.OUT)
    GPIO.setup(LED_value[2], GPIO.OUT)
    GPIO.setup(LED_accuracy, GPIO.OUT)

    GPIO.setup(btn_increase, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(btn_submit, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(buzzer, GPIO.OUT)
    # Setup PWM channels
    global pwm_LED
    pwm_LED = GPIO.PWM(LED_accuracy, 1000)
    global pwm_BUZ
    pwm_BUZ = GPIO.PWM(buzzer, 1000)
    
    # Setup debouncing and callbacks
    GPIO.add_event_detect(btn_increase, GPIO.FALLING, callback=btn_increase_pressed, bouncetime=400)
    GPIO.add_event_detect(btn_submit, GPIO.FALLING, callback=btn_guess_pressed, bouncetime=400)
    pass


# Load high scores
def fetch_scores():
    # get however many scores there are
    score_count = eeprom.read_byte(0)
    # Get the scores
    scores_list = []
    for i in range(1, score_count+1):
        scores_list.append(eeprom.read_block(i,4))
    # convert the codes back to ascii
    for j in range(0,score_count):
        for k in range(0,3):
            scores_list[j][k] = chr(scores_list[j][k])
    # return back the results
    return score_count, scores_list

# Save high scores
def save_scores(name, guesses):
    # fetch score
    score_count, scores= fetch_scores()
    # include new score
    scores.append([name[0],name[1],name[2],guesses])
    # sort according to scores in ascending order
    scores.sort(key=lambda x: x[3])
    # update total amount of scores
    score_count += 1
    # write new scores
    data_to_write =[]
    for score in scores:
        # get the string
        for char in range(0,3):
            data_to_write.append(ord(score[char]))
        data_to_write.append(score[3])

    eeprom.write_block(1, data_to_write)
    eeprom.write_byte(0,score_count)
    pass


# Generate guess number
def generate_number():
    return random.randint(0, pow(2, 3)-1)


# Increase button pressed
def btn_increase_pressed(channel):
    #ensure button only has effect if in play
    global play 
    if  not play:
        return
    # Increase the value shown on the LEDs
    global guess
    guess += 1
    if guess > 7:    #ensure guess stays in range
        guess = 0

    GPIO.output(LED_value[0], (guess & 0b001)!=0)
    GPIO.output(LED_value[1], (guess & 0b010)!=0)
    GPIO.output(LED_value[2], (guess & 0b100)!=0)

    pass


# Guess button
def btn_guess_pressed(channel):
    #ensure button only has effect if in play
    global play
    if not play:
        return

    global guess
    global guesses
    # If they've pressed and held the button, clear up the GPIO and take them back to the menu screen
    start = time.time()
    while GPIO.input(btn_submit) == GPIO.LOW:
        time.sleep(0.01)
    length = time.time() - start

    if length > 1.5:
        #clear GPIO, reset game values, end game and go to menu
        clear()
        reset()
        end_of_game = True
        menu()
        return

    #reset LED and buzzer
    pwm_BUZ.stop()
    pwm_LED.stop()

    # Compare the actual value with the user value displayed on the LEDs
    guesses += 1
    if (guess != value):
    # Change the PWM LED
        accuracy_leds()
    # if it's close enough, adjust the buzzer
        if (abs(guess-value)<4):
            trigger_buzzer()
    # if it's an exact guess:
    elif guess == value:
    # - Disable LEDs and Buzzer
        clear()
    # - tell the user and prompt them for a name (ensure at least 3 characters)
        name = input("You won. Enter your name: ") + "   "
        name = name[:3]
    # - Update scores and score count in sorted order on EEPROM
        save_scores(name,guesses)
    # - reset values, end game and return to menu
        reset()
        end_of_game = True
        menu()
    pass


# LED Brightness
def accuracy_leds():
    dc = 1.0
    # Set the brightness of the LED based on how close the guess is to the answer
    # - The % brightness should be directly proportional to the % "closeness"
    # - For example if the answer is 6 and a user guesses 4, the brightness should be at 4/6*100 = 66%
    if guess<value:
        dc = abs((float(guess)/value) * 100)
    # - If they guessed 7, the brightness would be at ((8-7)/(8-6)*100 = 50%

    elif guess>value:
        dc = abs(((8-float(guess))/(8-value))*100)

    pwm_LED.start(dc)
    pwm_LED.ChangeDutyCycle(dc)
    pass

# Sound Buzzer
def trigger_buzzer():
    dc = 5.0
    freq = 1.0
    # The buzzer operates differently from the LED
    # While we want the brightness of the LED to change(duty cycle), we want the frequency of the buzzer to change
    # The buzzer duty cycle should be left at 50%
    # If the user is off by an absolute value of 3, the buzzer should sound once every second
    if (abs(guess-value)==3):
        freq = 1.0
    # If the user is off by an absolute value of 2, the buzzer should sound twice every second
    elif (abs(guess-value)==2):
        freq = 2.0
    # If the user is off by an absolute value of 1, the buzzer should sound 4 times a second
    elif (abs(guess-value)==1):
        freq = 4.0
    pwm_BUZ.start(dc)
    pwm_BUZ.ChangeFrequency(freq)
    pass

#clear GPIO values and set to default
def clear():

    GPIO.output(LED_value[0],0)
    GPIO.output(LED_value[1],0)
    GPIO.output(LED_value[2],0)
    pwm_LED.stop()
    pwm_BUZ.stop()
    pass

#reset values
def reset():
    global guesses
    global guess
    global play
    global value 

    guess = 0
    guesses = 0
    value = 0
    play = False
    pass


if __name__ == "__main__":
    try:
        # Call setup function
        setup()
        welcome()
        while True:
            menu()
            pass
    except Exception as e:
        print(e)
    finally:
        GPIO.cleanup()

