Source: https://www.youtube.com/watch?v=U4ogK0MIzqk

00:00:02
 hi everyone and welcome to a new episode of coding adventures today we're going to be exploring the game of chats let's begin simply by creating the chessboard so we'll need two loops for the x and y axes or files and ranks if you prefer and to tell if a square should be colored light or dark we can just check whether or not the file plus the rank is divisible by two let's try running this code and here we have our very humble beginnings i expect i'll be staring at these 64 squares a lot in the coming days or

00:00:35
 weeks depending on how challenging this turns out to be so i'll tweak these colors to something a little easier on the eyes [Music] next we'll need some pieces and i found this nice design online which came along with some interesting additional ideas for a giraffe a zebra whatever this is and several more i think chess is confusing enough as it is though so i'll stick to these for now we then need to represent these pieces in code so i'll assign each type of piece a number along with a number for white and black

00:01:08
 these values could be pretty much anything but i chose these particular one so that if we look at a piece in binary the three bits on the right will tell us what type of piece it is and then the two bits on the left tell us if it has a color associated with it which can be white or black so let's now create an array of 64 numbers which will be the computer's internal representation of the chessboard these are all zero by default but we could place for example on square zero a white bishop and on square 63 a black

00:01:39
 queen and whatever else we want behind the scenes i also added some code for actually displaying the pieces i'm not sure if they're obscuring quite enough of the board at the moment though so let me fix that perfect now instead of setting up the board piece by piece in that array i'd like to support the standard notation called fen here's an example of a fen string which might look terribly cryptic at first glance but it's actually really simple we start at the top left square and here we have

00:02:09
 seven empty spaces followed by a lowercase k meaning there's a black king hiding in this corner we then go to the next rank and skip three spaces and here we have an uppercase n meaning a white knight you're probably getting the idea already so i'll spare you the tedium of going through the rest i've written up this little function to translate those fence strings into the format we're using and up at the top here i'll write out the fan for the starting position so we can load that in

00:02:41
 and here it is i've also implemented some simple drag and drop behavior for the pieces although it's not quite behaving how i hoped i'll go ahead and fix that quickly so now it's making the pieces disappear for some reason i'm rapidly losing faith in my ability to code anything but i have at last got it working and i think it's looking nice although of course nothing's really stopping me from sneaking in a move like this when my opponent's not paying attention so the first real challenge of this

00:03:15
 project is going to be calculating what the legal moves are in any given position [Music] so these are the indices of our squares and from any square we can move orthogonally like a rook by adding these offsets and diagonally like a bishop with these offsets i'll write out those values and then i'm going to make another little array and when the program starts up it's going to quickly calculate the number of squares to the edge of the board starting from each different square and going in every

00:03:46
 direction just so we can easily look up that information when we need it let's then define a little structure for holding a move now we'll just record the starting square and the target square of the piece we want to move we can then make a list of these moves and a function for actually generating them what we can do in here is just loop over all 64 squares and see what piece is on each square and we're only interested in the piece if it's the right color for whoever's turning it is to move

00:04:16
 let's focus for now on the long range sliding pieces that's the bishop the rook and the queen so in the sliding piece function we can loop over the eight different directions and for each direction we'll also have a loop for the number of squares that exist in that direction up to the edge of the board now of course our movement might be blocked by one of our own pieces so let's skip to the next direction if there's a friendly piece in the way then we can create the move going from

00:04:47
 the start square to the target square and add it to the list of possible moves finally if there's an enemy piece on the target square we'll be capturing it so then we can't go any further than that and we'll need to skip to the next direction there as well this should work for the queen which moves in all eight directions but if it's a bishop we only want to look at the last four directions or if it's a rook then just the first fall so i've added some logic here for handling that

00:05:14
 if we now try this out on the board the sliding pieces should all be obediently obeying the rules i then spent some time carefully implementing the rules for the remaining pieces but i'll spare you a detailed account of [Music] that so at long last the knights are free to leap about we can push the pawns and i've even got the hottest new moves from the 15th century like double pawn pushes and on [Music] pawns can also become queens or knights bishops and rooks if they prefer and we can castle the kings

00:06:09
 the only thing not yet implemented and it's kind of important is the concept of check right now if the king is under attack you can just ignore it so the moves at the moment are what's called pseudo-legal the easiest way i can think of for fixing this is a little gross but it's to take each pseudo-legal move play it on the board and then look at all the opponent's responses if any of those responses is a capture of our king we know that our last move must have been illegal and in that way we can filter through

00:06:38
 just the legal moves [Music] let's put this to the test quickly so here for example if i try move one of black's pawns we can see it has no legal moves if i select the knight though we can either block the check or capture the queen so now that we have legal moves let's create our first adversary one who plays moves completely at random round one fight [Music] okay it turns out that playing randomly is not really a viable strategy just for fun though let's put the computer against itself

00:07:19
 truly a beautiful game now i'd like to get the computer playing a lot better than random of course so experienced human players rely heavily on pattern recognition and intuition and even when calculating concrete sequences of moves they only really consider a tiny fraction of the possibilities with most being subconsciously rejected as irrelevant programming a computer in this way is not easy instead we want to play to the computer's strengths by crunching millions of possible outcomes to do that though move generation needs

00:07:48
 to be pretty speedy and mine is the exact opposite of that so much time rolled by as i mashed away at the keyboard trying out different ideas and of course fixing the seemingly endless supply of bugs i created along the way as i tried to speed up the move generation so that my computer would be able to look further into the future [Music] one of the things i did was take this old code for filtering out illegal moves and throw it away instead i'm now keeping track of all the squares that the opponent attacks

00:08:19
 so we can easily detect if the king is in check in which case it either needs to move to a safe square or some other piece needs to move to one of these orange squares to resolve the check of course this knight for example could block the check except that would reveal another attack on the king from this bishop so i also calculate these lines for limiting the movement of pinned pieces along with some other optimizations like keeping track of where all the pieces are instead of having to loop over the

00:08:47
 entire board to find them i was able to speed things up a decent amount now i've been moving pieces around for a while and it seems like everything's working correctly but it's possible i've missed something so i'd like to set up a little test let's write a function that gets all the legal moves and one by one makes them on the board it then recursively calls itself so that for each move it makes each of the opponent's responses and so on to infinity or more realistically until my computer runs out

00:09:17
 of memory and crashes to circumvent that i'll add a depth value that decreases with each call and when it reaches zero we'll stop going any deeper what this function is going to do is simply count the number of positions that are reached after a certain number of moves for example here's what it looks like with a depth of two ply which just means one move for white and one move for black the result if i speed this up quickly is 400 positions let's run this for a couple different

00:09:49
 depths and we can see the number of positions grows very rapidly with almost 120 million possible positions after just three moves for each side now what we can do is compare these numbers to the consensus that's been reached by other chess programmers and it seems to match but obviously there's a lot of scenarios that can't arise so early on in the game so let's try it out on this test position which i came across on the chest programming wiki okay fingers crossed so something in my code is wrong what a

00:10:24
 surprise to try figure it out i'm going to enlist the help of one of the best chess engines out there stockfish i'll enter the test position here and then i'll ask it to run the same performance test the fish of course gets the correct result but what's super helpful is it gives this breakdown of the number of positions after each move which i can compare with my output to quickly trace exactly which moves my program is getting wrong the mistake i made involved castling which surprised me because

00:10:54
 i'd so carefully followed all the little rules like if a rook moves then you lose the right to castle on that side even if it returns to its original square but in this position if black captures the rook i didn't think to count that as the rook having moved and so my program came up with this creative response [Music] another position that caught me out was this one here the pawn is pinned to the king by the rook and so it's unable to move but if i make some other move and black then pushes this pawn to up that

00:11:28
 breaks the pin another pawn is free to move again let me undo that move though because there's also that sneaky arm passang rule where a pawn that moves two squares can be captured as if it had only moved one square so that works but in this case that reveals the attack of the rook again and so the move is actually illegal with those fixed it's now passing all the tests i've thrown at it so far it's still slower than i'd hoped to be honest but i think it's time to start working on a more challenging

00:11:56
 opponent there've actually been some breakthroughs fairly recently in the exciting world of chess programming involving techniques like neural networks and monty college research which i'm very curious to learn more about but for now i'm going to go with a more old school approach let's begin by making an evaluation function to try gauge how good a position is to do this we can decide how much each type of piece is generally worth so knights and bishops are probably worth about three pawns each

00:12:25
 a rook is worth a little more and a queen is somewhere in the vicinity of two rooks we can then add up the value of each side's pieces like so and what we'll then do is subtract the one from the other to end up with a value that's zero if the position is equal positive if the side whose turn it is to move is doing better and negative if the other side is doing better obviously there's much more to evaluating a position than simply counting the pieces but this seems like a decent place to start

00:12:55
 we can now write a little search function which should look familiar because it's the same idea as that move generation test we did a few minutes ago but instead of counting the number of positions after however many moves it's going to evaluate those end positions we should also account for the fact that if there are no legal moves available then it's either checkmate in which case we can return negative infinity because what could be worse than losing a game of chess or it's stalemate which gets a

00:13:21
 score of zero now we want to keep track of the best evaluation so over here we can see what evaluation each move leads to and this negative sign is very important because a position that's good for our opponent is bad for us and vice versa let's visualize quickly what's going on so say it's black's turn in the current position and we're trying to choose between three possible moves to do that the search will look at white's possible responses to those moves and evaluate the resulting positions

00:13:52
 obviously we could search deeper than that but let's keep things simple so these three positions will be evaluated first and from that we can see that white should make this move which gives a score of six in white's favor then these three will be evaluated and white's best option is this move and finally these three are all in black's favor but this move is white's least worst option so in the original position we can now see that black should play this move to ensure an advantage even if white

00:14:22
 makes the best response now there's a trick for speeding this up if we rewind to this moment here we've just evaluated a position that's good for white in fact it's even better than what white was able to get over here so if you think about it that actually already rules out this move as an option for black and so we can take out our garden shears and prune this branch from the tree not wasting any more time on it this optimization is called alpha beta pruning and it gives the exact same results as a pure search

00:14:53
 just faster how much faster depends on the order of the moves because if by some misfortune they happen to be ordered from worst to best we can't prune anything at all essentially the more good moves are searched early on the more branches will be pruned and the faster it will be obviously we don't know in advance which moves are good that's the entire reason we're doing the search but we can make some guesses for example if we're able to capture a piece of high value say the opponent's queen with something

00:15:24
 of low value like a pawn that's very likely to be a good move also promoting a pawn is usually a good idea whereas moving a piece to a square that's attacked by an enemy pawn is usually going to be a bad idea so let's try all of this out on this test position i've set it up to search to a depth of four so it's looking ahead two moves for each side and with just the pure unoptimized search that took a little over a second and it had to evaluate about three and a half million positions

00:15:56
 i'll now go back and try this again with alpha beta pruning enabled and this time it finished in under a quarter of a second and only evaluated about a half a million positions for the exact same result let's do this one more time now with the move ordering optimization enabled this is brought it all the way down to 25 milliseconds and it only had to evaluate about 5000 positions this time i actually wasn't expecting it to be quite that effective so that's really cool to see anyway it does play a lot better than

00:16:27
 random now but still pretty terribly the trouble is when it reaches the maximum depth of the search it adds up the pieces to see who's ahead but of course that could change on the very next move if there's an unprotected piece somewhere so it's catastrophically misjudging almost every situation the fact is our evaluation function is only going to be remotely reliable if no piece can be captured on the next move so in our search function instead of just evaluating once the depth is reached

00:16:56
 we can start a new search that looks only at captures and just keeps going until no captures are left here's what that function looks like it's very similar to the regular search with a few small tweaks like of course we're now only generating capture moves and there's no depth limit anymore it might be a good idea to include checks as well in this function but i'm not going to worry about that for now just to get a better feel for what's going on here's the position we had earlier and

00:17:23
 here are some examples of positions that were evaluated during the original search as you can see there are captures possible all over the place with the addition of that secondary search though the final positions being evaluated now have no immediate captures available so hopefully the evaluations will be a lot closer to the truth now there are still many aspects of the game that the computer is completely hopeless at for example here's a position with a lone king versus two rooks which is of course easily winning for

00:17:53
 black the trouble is the computer can't see far enough ahead to find a forced checkmate and there are obviously no pieces it can try win so it just shuffles around aimlessly so i've added this little function to the evaluation script which just favors positions where the opponent's king is close to the edge or corner of the board because it should be easier to deliver checkmate there and it also incentivizes moving the king closer to the opponent's king to help cut off its escape routes

00:18:22
 and assist with the checkmate if necessary this only really applies to the end game though so this value increases in significance as the opponent has fewer and fewer pieces remaining let's see if this actually helps so black has used the rook to cut me off and has now brought the king a little closer now a check to force me to the edge and that's already checkmate i'll make it a bit harder by removing one of black's rocks so now the computer will actually need the king to deliver

00:18:49
 mate let's see how the machine goes about this it seems to be doing a very good job of forcing me to the edge and now a clever little retreat with the rook and it's mate once again let's try something different here black is up a queen but i'm on the verge of creating a queen of my own so black gives a check and my fear is that it will just keep giving checks forever and end up in a draw but actually it does seem to be maneuvering the queen closer and closer to my king and now it lands on a very important

00:19:21
 square because i can't move the king away here or else i'll lose my pawn so i'm forced to step in front of it blocking its stream of promotion now the black king has a moment to creep forward and when i move away to allow the pawn to promote black will hopefully lead me on this unpleasant little dance again where i'll be forced to step back in front of the pawn and this should continue until the black king is close enough to help deliver checkmate so this seems to be working and i think

00:19:47
 it's really cool that that simple tweak to the evaluation function enables it to solve quite a variety of end game positions of course there's still many more complex ones that are beyond its abilities at the moment but this feels like a good start here is an example of a much more complex end game white is winning we just need to sneak our king into black's half of the board to gobble up some pawns this is easier said than done though because playing this against stockfish here you can see that black is able to

00:20:16
 block our king from entering and if we head over to the other side we'll find our attempts thwarted there as well the truth is that after my very first move the position was already unwinnable white needs to find a very precise path starting with this move to outmaneuver the rival king to solve positions like this our program needs to be able to look very far into the future so let's consider the concept of transpositions which are identical positions reached by different sequences of moves

00:20:50
 currently we're wasting a lot of time searching and evaluating these identical positions when we could just store the results of the position the first time and look it up if we encounter it again now we can look up positions based on their fend string of course but these are relatively slow to generate and compare so instead i'm going to use a technique called zobrist hashing which is just a quick way of generating a single number to represent a position i'm using a 64-bit number which means

00:21:18
 there are over 18 quintillion possible values we can have which sounds like a lot but that's peanuts to the number of possible chess positions so with this approach we do run a risk of looking up an evaluation and unknowingly getting the result of a completely unrelated position what we can do about this is pretty much nothing if we want the speed we have to live in fear it should be pretty rare though so let's go back to this end game position and i'm going to play the black side now against our little ai

00:21:49
 i'll give it one second to think and it has found the correct starting move at least i hope this is going to work because the hashing and transposition lookup stuff was a real headache to get working and i'm pretty confident there are still some nasty bugs lucking in my code anyway i need to block the white king from entering on this side but our opponent has managed to orchestrate it in such a way that i believe i'm going to be too late to prevent it from sneaking in on the other flank

00:22:14
 [Music] i think it's doing a really good job here so now while i'm distracted with this pawn it's heading back over to the other side to eat up my other pawns i suspect this wasn't the fastest way to finish things off but it should definitely do the trick my last faint glimmer of hope is to get this pawn storming up the board but it's just too far behind in the race and i think the computers could be able to cut it off pretty easily i am getting very close to promotion although so it needs to be careful

00:22:46
 oh it actually doesn't care i guess if i make a queen it will simply checkmate me over here i have one last trick up my sleeve i can promote to a night checking the king but it just steps aside and now there's really nothing i can do very cheeky behavior from the computer okay so i'd say the most glaring weakness now is the computer's opening play it just shuffles pieces around because even with all the optimizations we've done it can't seem nearly far enough ahead to know that this will get into

00:23:16
 trouble sooner or later [Music] so we need to encourage it to put its pieces on reasonable squares and a simple way of doing that is to create a little map of bonuses for each square for the different pieces here's one for knights for example tempting them towards more central locations where they can control a lot of territory and here's one for the king for the early and middle stages of the game suggesting that it shouldn't wander too far from home and that it might find the most safety towards the outer edges of

00:23:55
 the board obviously these maps are very generalized and good squares will depend on where your other pieces are and of course where the opponent's pieces are and so on but this should be a helpful nudge in the right direction at least to test this out i'll try making some opening moves again and it seems to be responding a lot more sensibly now than it was before it's bringing out pieces and taking some sort of control in the center so that's very nice to see now it will respond the exact same way every time

00:24:26
 which is a little dull so to inject some variety i've downloaded a bunch of grandmaster games and for the first five or so moves i'd like the computer to pick a random move from these games to play if it can find the current position in there of course this collection of games is pretty small there are only about 8 000 or 7 here but it should be enough for now to give a decent variety of options at least in common opening variations all right now i set myself a deadline for this project which i've actually

00:24:55
 already exceeded by several weeks it turns out chess programming is quite the rabbit hole so even though there's a million things i still want to do i'm going to stop adding stuff at least for now and let's finally play some games to see how good our little adversary has become so black has played the nimzo indian and i never really know what to do here i'm going to try this it's a bit of a strange looking move but i saw it recommended in a video by grandmaster daniel neroditsky

00:25:29
 so if this goes badly i at least know who to blame [Music] actually i think i'm already messing this opening up to be honest but the computer is out of its opening book now so it'll have to figure things out on its own as well i should probably focus on getting my king side pieces developed so that i can castle to safety let me just capture here quickly first and defend my night thank you for a very enjoyable game [Music] so as i tried to take my revenge here i want to talk about an interesting

00:26:11
 problem that i glossed over earlier the problem is how do we decide what depth to search to because obviously we want to search as deeply as possible but we have to take time constraints into account now it's impossible to predict how long a search is going to take and if we stop the search before it's finished the results will be pretty meaningless because it won't have considered all of the opponent's responses yet when i was researching this problem i was initially a bit horrified by the

00:26:39
 solution i came across but it's actually really clever it has a slightly scary name iterative deepening but the idea is super simple we first do a search to a depth of one and when that's complete we then do a search to a depth of two then three and so on so this way we can of course interrupt it at any time and just use the results from the last fully completed search the reason i was horrified though is that each time we start a deeper search we're redoing the work of all the previous searches we've done

00:27:11
 it seems like a huge waste of time especially because we can't even use all the evaluations stored in the transposition table because they're not helpful if they come from a shallower search than we're currently doing but and this is a big but remember that with alpha beta pruning if we look at good moves first it will be able to prune more branches and so what we can do is keep track of the best moves during each search and look at those first in the next deeper search the deeper search won't always agree

00:27:41
 that those are good moves but a lot of the time it will and it turns out that the increased amount of pruning that this leads to means that counterintuitively the iterative approach is often even faster than just doing the whole search once i'm not sure if that explanation made any sense but i hope so because i thought this idea was really interesting [Music] okay so i've played a bunch of games behind the scenes by now and i'm able to win most of the time so the computer obviously has lots of room

00:28:15
 for improvement in all aspects of the game but i think there are two main weaknesses the first is its very poor understanding of king safety which means it often thinks it's doing fine and then suddenly realizes it actually needs to start sacrificing pieces in order to stave off checkmate the other is its understanding of pawn structure or rather the total lack thereof it likes to advance pawns up the board to try promote them but it has very little ability to judge if a pawn is weak or strong which causes it to

00:28:45
 happily go into a lot of really bad positions so i'd like to come back to this project at one point to try address these issues and hopefully make it a much more formidable opponent but i think this is an okay start and i definitely had a lot of fun working on it so thanks for watching to anyone who might have made it this far i know it was quite a long journey but i hope you found it interesting until next time cheers

