# 50-Watt-LDMos-Amp
Inspiration for this project came from here: https://ludens.cl/Electron/50Wamp/50Wamp.html 

A 50 Watt HF Amp that uses modern parts 

This is mostly clanker code for a raspberry pi pico controlled protection loop and operation control for a 50 watt HF Amplifier that uses modern LDmos transistors instead of the IRF series mosfets that are 50 years old and inappropriate for this purpose. 

This is ultimately intended for use as a portable amplifier aimed at SOTA and to a lesser extent POTA operators who want to add some power to their QMX or other QRP radios. The majority of designs available on the internet are built around the IRF 510 or IRF 530 mosfet, and while it's impressive that an hf amp can be built around those parts, they're not very well suited to the purpose. This is designed around the AFT05MP Dual LDmos from NXP, which is currently not recommended for new designs. It's a dual ldmos rf amplifier designed to work up to 530 Mhz. Another rf power transistor that could be substituted would be the BLP5LA55 series LDMOS from Ampleon, which are newer but don't come in the handy dual package. There aren't a lot of 12-15 volt RF mosfets on the market. We're a small niche.  

Principle design goals are as follows: 

-12 volt operation
-Uses actual RF power transistors, preferably ldmos
-No unobtainium parts
-Currently manufactured components only
-Keep parts reasonably affordable
-Smaller heatsink with shortened fins and permanently mounted cooling fans for improved portability 
-Ruggedized, completed design, meaning full protections from drain overvoltage, overcurrent, oscillation, and overtemperature
-Able to be used in line with an antenna tuner!!!!!!!! (Seriously. A portable amp is next to useless without that capability. Finish the design job.) 
-40-10meter operation. Requires only three filter banks. Don't care about the other bands. This is for portable use. 50 watts won't get you over the noise floor on 80 meters anyway.  
-A real Keyer input. No RF sense keying. It's annoying to use. 
-Manual band switching. 
-Always <2:1 input SWR. The amp should never under any circumstance cause the QMX to shut off. 
-Amp shuts off in response to excess current and drain voltage excursions, not high SWR. High SWR doesn't kill transistors. High drain voltage and overcurrent does. 
-Display all relevant parameters and return comprehensible error codes 
-Maybe full QSK. We'll see. Would be nice but not a specific deal breaker. 
-Maybe Variable input attenuation to compensate for QMX low output on 17 and 21 meters. Cool idea but requires some deep thought. 



