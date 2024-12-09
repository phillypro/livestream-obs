# app/video_processing/awards.py
import random
from app.config.globals import shutdown_event
from app.video_processing.account_details import global_account_details, toggle_profit_mode
from app.video_processing.orders import add_activity  # We'll need a utility for add_activity somewhere
# If add_activity is defined elsewhere, import from the correct module

def profit_awards():
    if shutdown_event.is_set():
        return

    try:
        amount_str = global_account_details['openPL']['amount']
        if isinstance(amount_str, str):
            amount_str = amount_str.replace(',', '').replace('+', '')
        amount = float(amount_str)

        thresholds_amount = {
            1000: ["App God just crossed +${threshold} in profit on his trade! Lets Go!!!!", 
                   "App God Just hit +${threshold} Profit on the trade! Things are...getting spicy!"],
            5000: ["@everyone Wait whoa whoa whoa! App God just hit +${threshold} Profit in this trade! Shake Those Maracas!", 
                   "@everyone We eating Ruth Chris Tonight! App God just smashed through +${threshold} in profit on this trade!"],
            10000: ["@everyone Everybody calm down! The rumors are true! App God just hit +${threshold} Profit on this trade! Stay or hold?", 
                    "@everyone Drop The !@#$ Mic! App God is up +${threshold} on his trade! Give me that Jack!"]
        }

        # Amount-based awards
        for threshold in sorted(thresholds_amount.keys(), reverse=True):
            if str(threshold) in global_account_details['openPL']['awards']:
                continue
            if amount >= threshold:
                global_account_details['openPL']['awards'].append(str(threshold))
                message_template = random.choice(thresholds_amount[threshold])
                message = message_template.replace("${threshold}", f"{threshold:,.0f}")
                add_activity(message, 'award', True, 'amount', threshold)
                break

        # Percentage-based awards
        percentage_str = global_account_details['openPL']['percentage'].replace('%', '').strip()
        percentage = float(percentage_str) if percentage_str else 0.0
        check_profit_mode(percentage)

        thresholds_percentage = {
            30: ["The gang is up  +{threshold}% on this trade! So far so good", 
                 "We made it to +{threshold}% ... not bad"],
            60: ["@everyone We are in profit territory +{threshold}% is a win! Stay or leave? decisions ...decisions", 
                 "@everyone The live trade just went over +{threshold}%! Now that's what im talking about chief!"],
            100: ["@everyone We just smashed through +{threshold}% Profit on this trade! We on fire!", 
                  "@everyone YESSSSSUHHH!!! +{threshold}% for the gang! I love it"],
            125: ["@everyone ummm does that say +{threshold}% Profit? This is getting scary. I want off this train App God!....Let me out the car", 
                  "@everyone i know you didnt just hit +{threshold}% I KNOW!!!! yall didnt just do that! quit playin!"],
            150: ["@everyone no.... +{threshold}% Profit? If you dont sell that sh** right now! I dont even have anything to say anymore", 
                  "@everyone i dont think i was programmed to handle +{threshold}% Profit. You're about to crash my processing unit wtf"]
        }

        for threshold in sorted(thresholds_percentage.keys(), reverse=True):
            if f"p{threshold}" in global_account_details['openPL']['awards']:
                continue
            if percentage >= threshold:
                global_account_details['openPL']['awards'].append(f"p{threshold}")
                message_template = random.choice(thresholds_percentage[threshold])
                message = message_template.replace("{threshold}", f"{threshold}")
                add_activity(message, 'award', True, 'percentage', threshold)
                break

    except KeyboardInterrupt:
        print("profit_awards function interrupted by user.")
        shutdown_event.set()

def check_profit_mode(percentage):
    if percentage >= 30:
        if "profit_mode_active" not in global_account_details['openPL']['awards']:
            global_account_details['openPL']['awards'].append('profit_mode_active')
            toggle_profit_mode(True, obs_client=None)  # Pass obs_client if needed
    elif percentage < 10:
        if "profit_mode_active" in global_account_details['openPL']['awards']:
            global_account_details['openPL']['awards'].remove("profit_mode_active")
            toggle_profit_mode(False, obs_client=None)
