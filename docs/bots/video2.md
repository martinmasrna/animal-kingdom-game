Source: https://www.youtube.com/watch?v=_vqlIPDR2TU

00:00:00
 hello everyone welcome to another episode of coding Adventures today we're back to chess so what I'd like to do is take this little chess playing program that we made about two or three years ago now and figure out how good it actually is my plan for doing that is to Simply Let it Loose on a popular chess website called leeches as a registered bot account of cons and see what sort of rating it ends up with before we do that though I can't resist trying to make it just a little bit stronger so that it's hopefully able to

00:00:35
 put up a good fight now to test whether the changes we make are actually helpful or not I've started by making a little program called the match manager and the idea is that we'll be able to connect up two different versions of our chess program so we can have the new version battle the old version to make sure we haven't accidentally made it worse they need to play a wide variety of positions for it to be a good test though so I'd like to start each game from a random position to get some random test positions I've

00:01:07
 gone over to the leeches database to First download a bunch of games wait a minute this is 35 gigabytes for one month of games that's that's too much chess let's go back in time to something a bit more manageable okay 500 megabytes I can work with [Music] so we now have this file of two and a half million games in the portable game notation format and I like that it also includes the name of the opening because if we choose games that started with different openings that should ensure

00:01:37
 some more variety in our test set okay I've just finished struggling to write some simple python code for a change because I wanted to use this nice library to extract random positions from the games where there are still lots of pieces left to avoid any totally boring positions running this took a couple of minutes to finish but if we just fast forward time we now have a list of physicians in the fan notation that we talked about last video which I only want Physicians that are roughly equal for our test set so with

00:02:09
 some help from the internet I've managed to get some code working that automatically feeds each position into stockfish one of the strongest chess programs in existence to filter out all the ones that are unfair to either side with that done I'm going to try running a full match between two copies of version one just to make sure that everything goes smoothly they're playing 500 different positions both as black and white so a thousand games in total with a generous thinking time of 100 milliseconds per month

00:02:42
 this will probably take a few hours to run so feel free to have a nap and I'll wake you up when it's done you won't fish up till then that it was a pretty even match between version 1 and version 1 with the one version one winning 347 games and losing 355. so with our test setup working let's try to actually improve the program I'd say there are two main areas we can focus on search and evaluation and let's start with search because while that test was running I've been looking back

00:03:14
 at some of this old code and I noticed something nice and easy that we can begin with so we're doing something here called iterative deepening which is a fancy name for just first searching one move ahead then if the search hasn't been canceled yet we increase that to search two moves ahead and so on and that way no matter when the search is canceled we'll always have the move from the previous iteration ready to play at least that's what I thought when I wrote this I thought that once the

00:03:42
 search is canceled we just have to throw away all the work from the current unfinished iteration because how could we trust what it says is the best move when it hasn't looked at all the possible moves yet but that's a bit silly because so long as we begin each new search by looking at the best move from the previous iteration then say the search is canceled halfway through either it will still think that's the best move in which case no harm done or it will have found a better move which we should

00:04:10
 obviously take so I'll change things around a bit here so that it accepts the new result even if that search iteration was incomplete and then in the giant mess that is the main search function I'll just make sure that when we're choosing the order in which we're looking at the moves we guarantee that the best move from the previous iteration comes first okay so let's just play a few moves to make sure I haven't broken anything okay it looks like I've broken something

00:04:38
 it wants to make the move A1 to A1 which is definitely not allowed that's actually how I represent a null move because to try to be efficient with memory during the search I in fact all the information about a move into a 16-bit value with the first six bits giving the index of the stat Square the next six giving the index of the target square and the last four bits being a flag for things like promotions and so on so an invalid or null move which I've just assigned the value 0 tells us to

00:05:09
 move from Square 0 to square 0 which is A1 to A1 so I guess the problem arises if the search iteration is canceled before it can even finish looking at the fast move meaning we just need to add a little note check over here all right with that fixed I've set up a match and let's see how it goes okay the results are in for version 2 versus version 1 and we have 141 wins to 836 losses clearly I've made a huge mistake I have no idea what it is though so I started by looking at some of the games

00:05:53
 it played and it is making catastrophic blunders like playing Queen B6 in this position where it can of course just be captured by the bishop delving into the search logs we can see it begins by wanting to play The Far More sensible Knight F6 and this remains Its Top Choice through all the iterations where it thinks it's a little bit worse until the search is canceled when it suddenly thinks the position is dead equal and blund is the Queen instead okay this has led to me discovering a really sloppy mistake in my old code

00:06:24
 which is that when the search is canceled it returns zero immediately at the top of the function which is fine but what evidently slipped past me's mind is that this is a recursive function so that's not the end of the story that zero is going to show up as the evaluation over here so if it thought the position was worse before sunlight sees wow I can get an equal position by making whatever random move the search happened to be canceled on the only reason this wasn't wreaking havoc before is that I was wastefully

00:06:54
 discarding the results from the unfinished search but now that we are using those results we can just add another exit Point here so that we do actually quit the search immediately alright running the Test match again with this fix gives us a score of 409 wins to 270 losses which is much more encouraging something I realized while this was running though is that before we fixed the search to actually exit immediately when canceled those faulty evaluations would have been stored in the transposition table which is just a

00:07:26
 giant lookup table we use to avoid constantly re-evaluating positions that we've come across already so up here where we're starting the search I had originally left this bewildered comment about having to completely clear the transposition table before each new search to ward off mysterious blunders I guess now we know why I am very excited to delete this horrible little line of code and now with the stored evaluations persisting across moves the set should be a lot more efficient so let's run a test

00:07:57
 against our previous version alright this is come back with 399 wins to 387 losses which is very underwhelming I rarely expected that to make a bigger difference okay I've been investigating a bit because I was confused by that result and what I'm seeing is that the transposition table is getting filled up suspiciously quickly meaning it very soon has to start overwriting old positions the reason it's suspicious is that I'm using a gigantic one gigabyte table and there's no way it should be

00:08:31
 filling up that fast okay my face is starting to hatch from all the face palming I'm doing today I have some code for reporting the size of the transposition table and it does this by first figuring out the size of each entry in bytes which it then multiplies by the number of entries divides by a thousand and says that's the size in megabytes the study maths means that the table wasn't a whole gigabyte like I thought but actually just about one megabyte while we're here fixing this let's

00:09:01
 actually quickly change this calculation around so that instead of specifying the number of entries we want we'll calculate the number of entries based on the desired size in megabytes because that's a much more intuitive setting and let's maybe set it to a modest 64 because that seems nice and thematic I'll then try this out again on the same position and we can see that it's filling up a lot more slowly now so I'll run the match once more with the new 64 megabyte table and this time we

00:09:31
 get 386 wins to 246 losses so a fairly significant upgrade now I think always testing against the most recent version is a good way to judge if the program has improved but to keep track of our overall progress I also want to keep a record of how each version compares to the original version 1. so far we have version 1 against itself not terribly interesting then there's version 2 which no longer wastes the result of incomplete searches and now we can add our latest build with the fixes to the transposition table and

00:10:06
 against version 1 that is scoring 484 wins to 218 losses now I've been spending a bit of time doing some research trolling through various discussions and heated arguments on Old chess programming forums trying to find this specific version of an archive of a site where the link to the article I want to read actually works and of course going down the incredible rabbit hole that is the chess programming Wiki where one moment you're reading a mundane article about the names of different types of nodes in a

00:10:38
 search tree and the next you blink and suddenly it's dark outside and you find you're Consulting a chat about the movement of knights and how that relates to the orbital period of mercury and you ask yourself how did I get here suffice it to say I have plenty new ideas to try now one of these is a technique called such extensions so at the moment we look equally deeply into all moves but it is probably wise to pay special attention to the most potentially interesting ones for example we could say that if the

00:11:11
 current move puts the opponent in check then we'll extend the search to go one move deeper to prevent things from potentially getting out of hand though I'll set an arbitrary limit on how deep these extensions can actually take us all right I've tested this in a match against our previous build and it scored 433 wins to 237 losses which is a really nice Improvement for such a simple idea I also tested it against version 1 for interest sake where it scored 561 wins to 169 losses so we're seeing some

00:11:47
 pretty consistent progress so far and hopefully it's gonna stay that way okay I've just quickly separated out the extension logic to its own tiny function because things are getting quite cluttered but it's doing the same thing as before so now let's try extending the search for other types of moves as well for example if a pawn is on the verge of promoting we should probably keep searching to find out whether that's going to be successful or not so let's find out what type of piece was

00:12:14
 moved and also what rank it was moved to and then we can just write a little if statement that says if we've just moved upon and it's now on the seventh rank so index six or the second rank which is index one then we'll want to extend the search by one move and let's see if this extension also makes such a big difference it made a big difference alright we're now getting 107 wins to 610 losses that's very unfortunate okay I was about to delete this code when I realized I've actually blunded my

00:12:49
 brackets here the problem is just that and has a higher precedence than all so we're not actually testing if a pawn has reached either the seventh or the second rank but rather if a pawn has reached the seventh rank or something has just moved to the second rank so that means we're extending loads of totally uninteresting moves and wasting an enormous amount of pressure search time so let me fix that quickly and run the match again okay this time the score has ended up at 337 wins to 273 losses not nearly as big

00:13:23
 a difference as the check extension but definitely helping out a little as always I'll also test this against version one but it actually doesn't seem to be doing any better than the previous build there which is a bit surprising to me but I guess it makes sense that improving against one opponent doesn't necessarily guarantee that you'll play better against a different opponent anyway I've been experimenting with a few other extensions behind the scenes such as extending if a pawn actually

00:13:52
 manages to promote to a queen and also extending when a player has only one legal move available but this didn't seem to help the program at all so I'll leave them out [Music] while all these tests have been running I've mainly just been going through and refactoring all the code since I left it in quite a mess last time there's nothing exciting to show from a list of costs everything should behave exactly the same as before except that's not how chess Works what have I done

00:14:23
 okay this first move Advantage is getting out of hand fortunately I was able to enlist the help of a professional bug Hunter who was very helpful in fixing the problem alright so with the code tied it up and everything behaving again let's get back to making the engine stronger we've spent a bit of time improving the search already so let's work on the evaluation a bit for a change at the moment our evaluation function considers just three simple terms the first of these is the amount of pieces

00:14:55
 on the board so it adds up the number of Pawns multiplied by the value of a Pawn Plus the number of nights multiplied by the value of a knight and so on and of course these are just very generalized estimates of what each piece is worth the second term takes into account where on the board each piece is located so for example these are the square scores for Knights meaning that Knights on more Central squares will be valued more highly since they're able to control more squares finally the third term is this mop-up

00:15:26
 skull basically when we have an advantage in the end game we want to encourage the king to move closer to the enemy King to help push it to the edge of the board where it's easier to deliver checkmate here's an example of that term in action now I think the program plays surprisingly well for having such a limited understanding of the game which let's try giving it some extra knowledge to work with to begin with let's take a look at those Square scores again this time for the king

00:15:57
 we can see that these scores are simply encouraging the king to find shelter on either edge of the board and discouraging him from charging into enemy territory because he's not a very good fighter once the dust of the opening in Middle game has settled though and we move into the end game phase with not so many scary pieces left on the board the king should stop cowering in a corner and start thinking about being useful for once in his life by supporting the advancement of the friendly pawns or

00:16:27
 getting in the way of the enemy Pawns so I have a second table of King Square scores here to entice the king to move more towards the center of the board and we can just blend between these two tables based on the number of remaining enemy pieces I actually started implementing this last episode already but ended up leaving it out because I felt like the King was being a bit too aggressive and I didn't have the energy to tweak and test it now that we have this nice little testing framework though we can just let

00:17:00
 the match run and see how it goes [Music] okay the results are in and the side with the aggressive King has ended up with 385 wins to 276 losses not bad and playing against version 1 it's now scoring 630 wins to 137 losses that was pretty effective so let's try doing a similar thing for the Pawns currently they're being encouraged to move up the board to become Queens but we also have this conflicting goal of holding back these two groups of Pawns here and here in case the king wants to

00:17:42
 take shelter behind them in the end game we don't need to worry about that as much though so I've added a second pawn table to the code for the endgame and let's just quickly set up some scores here I'll give both the second and third rank a score of 10 because From upon's perspective they're the same distance from the end of the board and then we can just increase the score for each subsequent rank okay I'll now employ my highly sophisticated system of copying the string of values this little editor

00:18:11
 prints out and then pasting that into the code alright testing this we've ended up with a small Improvement of dubious significance 365 wins to 353 losses I'd be curious to know the probability that the new version is actually better than the old version based on this score so if there are any statisticians watching please let me know how to calculate that anyway against version 1 it actually does seem to have helped to fabric taking us up to 670 wins to 142 losses so that's nice to see at least

00:18:47
 alright so with this table we're encouraging all pawns to move up the board in the end game but certain pawns are going to have a better chance of becoming Queens than others for example this white Pawn on the left here is blocked by the black pawn in front of it so it won't be able to make it through on its own then this Pawn in the middle does have a clear path ahead of it but it's probably going to be captured along the way and finally this Pawn over here is known as a past Pawn because there are no enemy pawns that

00:19:18
 can block or capture it on its path to queendom each old chess wisdom tells us past pawns must be pushed so I reckon we should give our butter bonus for doing the same but first we need an efficient way of actually detecting these past pawns and I'd like to try to do that using bit boards so a bit bored is really just a single number that represents some aspect of the current position for example the number is 65 280 would represent the locations of all the White ponds in this position that'll make a lot more sense if we look

00:19:53
 at the number the way the computer sees it though which is to say as a 64-bit binary number in this case made up of 48 zeros followed by eight ones and finally another eight zeros so in the code we can represent a bit board as a ulong which is just a 64-bit integer and I'll actually make an array of these so that we can have bit boards for all the different types of pieces if we want now there are a bunch of different operations we can do with binary numbers for example the bitwise or operation of

00:20:25
 a and v gives us a binary value with ones in the places where either A or B is set to 1. then there's the end operation which gives us this with ones in places where both A and B are set to 1. we also have the exclusive or operation which gives us this with ones in places where either a is set to 1 or B is set to 1 but not both another useful tool we have are these left and right shift operators so for example if we take the value 1 and shift it four bits left we get well exactly what you'd expect

00:21:04
 so in the code when we're loading in all the pieces for the starting position we can look up the bit board that corresponds to the current piece type and do a bitwise or operation on its current value with the value 1 shifted over by the index of the square that that piece is on and that will set up all our bit boards of course we also need to update them whenever a piece is moved so over here we can just look up the bit board for the type of piece we're moving and use the exclusive or operation this time to

00:21:34
 toggle the bits so that the starting Square gets set to zero and the target Square gets set to 1. also if this move captured a piece we'll need to make sure that on the bit Board of the captured piece type the target square is toggled to zero I think that should work but let's try it out to make sure so I'll move this Pawn up and we can see the start Square was toggled off and the target Square toggled on let's also make sure that captures are working so I'll let the Knight snack on

00:22:04
 this pawn and it has been removed from the bit board so this seems to be working well although I just realized something actually there's that pesky on percent move of course always making my life just a little bit more difficult all right I've been working on this for a while and I think I've covered all of the edge cases we do only need the pawn bit boards at the moment but I got a little carried away and created this test interface here so we can easily flip through the bit boards for all the

00:22:35
 different pieces and make sure they're working Let's test that on person capture first so I'll set up a position quickly and that's looking good another Edge case is castling because of course when the king moves we need to update not just its bit board but the Rooks bit board as well and then finally if a phone promotes to a queen for example then that promotion Square needs to be added to the Queen's bit board and removed from the pawns bit board we can also do things like have one really long

00:23:07
 line of code that all together all the bit Boards of the white pieces for example and that will give us a single bit board telling us the location of every white piece which could maybe be useful in the future I don't know I'm just messing around a bit here to be clear though this bit board can't tell us what type of piece is on each Square which is why we need multiple bit boards to fully represent the position this actually reminds me of a really great video by Tom 7 where he creates

00:23:35
 all sorts of strange chess spots one of which is peace blind meaning it just gets two bit boards one for the white pieces and one for the black pieces and has to try figure out what to do from there anyway if you haven't already left to watch that far more entertaining video let's find a yet to work on the past Pawn detection we wanted to do so to tell if this is a past Pawn for instance we need to look at these squares in front of it and see if there are any enemy pawns there so let's try calculate

00:24:03
 a bit mask that covers this region as a starting point let's just write ulong.max value and that'll give us a bit bored with all bits set to one now we should be able to move this whole mask up the board by shifting all the bits eight spaces over that's not the direction I wanted let me try that again okay so that shifts everything one rank up but we want to shift it three ranks in this case since that's where the spawn is so in the code I already have a function for converting a square index to a rank

00:24:37
 index and we can just multiply the H by that rank index plus one with that we've managed to isolate the squares that lie ahead of the pawn but we're only actually interested in the three files surrounding the pawn where it can be blocked or captured by an enemy Pawn so let's start now by figuring out a mask for just a single file like the a file here for example I can't think of a clever way to do this so I guess we'll just write it out by hand every eighth bit should be a one so one

00:25:08
 two three four five six seven eight one two three four five six seven eight one two three four five six seven eight one two three wait a second there's a much less painful way to do this hexadecimal to the rescue alright so here is our a file mask and now we can just shift this around however we want so if we calculate the file index for the given square and then shift the a file mask by that many bits here's what we get now we also want to include the two adjacent files so for the file on the

00:25:37
 left that just means shifting one less and on the right would be shifting one more we don't want to go off the edge of the board though because that'll wrap around weirdly so let's do some quick clamping and then we can just combine all three of those together into a triple file mask by oring them together foreign [Music] we just need to combine the two masks into one so let's take that forward mask we calculated earlier and return that but ended with the triple file mask so that only where both masks have their

00:26:12
 bits set to one will actually end up as one and after all this messing about we've managed to create the past Pawn mask we wanted behind the scenes I've also made a version for the black pawns going in the other direction okay now to make use of all this I've written a little function that evaluates past forms so for each of our pawns on the board we get the appropriate past Pawn mask which has been pre-computed and stored in an array and then we can simply end that with the Enemy Pawn bit

00:26:41
 board and if that results in zero it means that no enemy pawns are in the way and so it is a past Pawn calculating it like this should be pretty efficient since we don't need to Loop over all the enemy pawns to find out if they're in the way or anything like that anyway we give each of these past pawns a little bonus and here are the bonus values I've chosen so we have 90 if the phone is one square from promoting 60 if it's two squares from promoting and so on now these numbers have been pulled from

00:27:11
 thinner so we should actually test and tweak them at some point to try to figure out what values would actually work best but for now let's just run a little test match and see how it goes all right We've Ended up with 415 wins to 325 losses which is a decent Improvement I'd say and against version one we can see a rather modest improvement over last time with 687 wins to 137 losses now a past Pawn is even more valuable if it's protected by another Pawn because obviously that raises its chances of

00:27:47
 surviving so I've added some code for detecting and rewarding that but mysteriously it's actually just made the program play a little bit worse so let's try something else instead in this position white has two pawns that are isolated which just means that there are no friendly pawns on the adjacent files that could ever support them and in general these are a bit of a liability we can very easily use our bit boards again to test for these isolated pawns and apply a penalty depending on

00:28:16
 how many they are trying this out in a match we get a mod is 396 wins to 341 losses against the previous version and against version 1 we're now up to 717 wins against 139 losses all right so we've improved the evaluation function a tiny bit which now that we have all these bit boards set up I'd like to try using them to speed up our move generation using an interesting technique called Magic clipboards beginning with the Rook I have so far just calculated a bit board for each of the 64 starting squares which simply

00:28:54
 tells us which squares The Rook is able to reach from there that's assuming the board is completely empty though of course in reality there is usually going to be some annoying pieces getting in the way what we're aiming for here is to be able to take this bit Board of all the pieces that lie along the path of the rook and use it as a key to look up what moves The Rook is legally able to make so essentially we want to pre-compute the legal moves for every possible arrangement of blocking pieces so that

00:29:25
 the move generator has less work to do at runtime now technically only the first piece that The Rook Encounters in each direction is actually blocking its path any pieces after that are irrelevant so we could reduce the size of the lookup if we ignore those irrelevant pieces since that's fewer configurations we need to store unfortunately that would mean that whenever we want to look up the legal moves we would have to have a loop running in every direction to find out where that first piece is that's

00:29:55
 blocking the path but that's essentially how the move generation works at the moment and is exactly what we're trying to avoid so for the sake of speed our lookup table is going to have to include lots of redundant peace Arrangements anyway that means that our task now is to figure out all the different possible Arrangements of pieces along these four directions the way I'm thinking about this is that we're essentially counting in binary so for example this would be one in binary

00:30:23
 and we can see that up here and so this would then be two this would be three four five six seven and so on but remember we don't care about these squares only about the squares where the Rook can potentially move so instead we're going to say that only places where this movement mask is set to one are actually valid binary digits so in that case this would actually be one since that's the first valid Place according to the movement mask and so this would then be two this would be three

00:30:55
 four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen and so on for all 16 384 different possibilities so that leads us to a nice and easy way to implement this in code which goes like this we're given the movement mask and we start by just creating a list of the indices of all the bits that are set to one in that mask so for this mask for example that's index 4 index 12 index 20 and so on now the total number of piece Arrangements we're going to have is

00:31:35
 simply however many numbers can fit in that many bits which is just 2 to the power of the number of bits we're then going to count from zero up to the total number of possible piece arrangements and for each of them simply take the current number and shift each of its bits into the valid places so just as an example say we're on number 13 which in binary is one one zero one all that the code does is shift those bits into these places here like this and that represents this arrangement of pieces

00:32:06
 so we're using that code we can now browse through all the different patterns so here we have landed on 4081 then here is 10 815 and here's where it ends okay so what I've done now is just made a gigantic dictionary by looping over every Square on the board then generating all the arrangements of pieces that could block the Rooks movement from that square and finally just figuring out what legal moves The Rook would have in each of those cases and adding that information to the dictionary

00:32:38
 so now given the square The Rook is on and the current arrangement of block is we can just directly look up the bit Board of legal moves and we can see that seems to be working one important detail though is that these blockers are all being treated like enemy pieces meaning The Rook can move onto them to capture them so we'll need to add a fix for friendly pieces later on but anyways since we're treating them like enemy pieces that actually means that for the last Square in each Direction it doesn't matter if

00:33:07
 there's a blocker there or not the result will be the same regardless and so we don't need to include those in the piece Arrangements we're generating which greatly reduces the size of our lookup table another important detail is that if I try place a blocker somewhere over here for example that's going to break everything because it's not a pattern that we included in the dictionary so in the move generator when we want to actually figure out what moves a rook is able to make from a session Square we

00:33:34
 first combine the friendly pieces and enemy pieces into a single bit board and then end that with this mask here the mask looks like this it's just the movement mask but stopping one square short in each Direction like we talked about that will clear out any pieces from squares we don't care about so that we end up with a valid key which we can then use to look after the move bit board from the dictionary finally we just have to extract the squares that The Rook can move to from that bit board using this efficient

00:34:04
 little Loop over here right now though The Rook is able to capture friendly pieces since we're treating old blockers as enemy pieces so to get around that we just need to take the bit Board of friendly pieces then invert it meaning the ones become zeros and the zeros become ones and then use that to clear out the friendly occupied squares from the move spitboard finally a little bit more fiddling was required for handling things like pins and checks but that was fairly easy to adapt from the ultimate generation code

00:34:36
 so after all this work I am excited to announce that the move generation is about 20 slower [Music] for possibly the first time ever though I think my code is not actually what's slowing things down but rather the problem is this standard dictionary we're using obviously it is designed to be fast but it does also have to be general purpose whereas we have a fixed set of data that we know ahead of time and so we can create a lookup table optimized specifically for that data so as an example let's say we have the Rook on

00:35:10
 this Square here and we also have some bit Board of blockers from that we want to generate a key which is simply going to be the index into an array where the corresponding bitboard of pre-computed valid moves will be stored now we can't just use the block as bit board directly as the index because this number is huge it's in the quadrillions and it would be preferable if our lookup table could actually fit in the computer's memory so the first thing we need to do is get our hands on a magic number

00:35:41
 and what's magical about it is that it has a special property that we don't know how to calculate we just have to try lots of different random numbers until we find one that works now this special property is that when we multiply it with any of the possible blockabit boards for the current starting Square the result will have all the important bits as far on the left as possible with the bits further to the right being basically garbage and I'll explain what I mean by that in a moment

00:36:08
 but then we're going to shift everything over by some number of places so that only these allegedly important bits remain leaving us with a reasonably small number which will be our index into the array so this Pitfall of moves we have here is going to be stored at index 131 and assuming that our magic number and our shift value were well chosen then this index will be unique to this particular movement board so when I talked about some of the bits being important and some being garbage the garbage is just all the bits to the

00:36:42
 right that we can get rid of and still end up with a unique index so as we've seen already this moves bit board will be stored at index 131. if we remove this blocker over here though we get a different move bit board and that's going to be stored at index 127. then this one will be stored at 8.95 this will be stored at 383 and so on the point is just that the indices are unique so that we don't end up overwriting one of the values in the lookup table with a different value of course we can only guarantee this

00:37:17
 unique mapping because we know all of our data ahead of time meaning we can literally just keep trying different magic numbers until we find one that works however finding a single magic number that works well for all 64 squares that it could be on is not really possible so we can simplify the task by just having a separate magic number and array for each of the 64 squares okay so here's what running the Brute Force set for the magic numbers looks like and you might notice I'm also generating magic numbers for a lookup

00:37:49
 table of Bishop moves which works exactly the same way as The Rook now we can see up here that the Rooks lookup table is around two megabytes in size but that will actually get smaller if we let this run for longer because it will gradually stumble across better magic numbers that allow the data to be packed into smaller arrays so after letting this run for a while I simply saved the result to a file and then pasted that into these arrays here then in the move generator we can just quickly update our code here to

00:38:20
 calculate the lookup index using the appropriate magic number and shift value and then this Rook moves lookup is now a two-dimensional array instead of a dictionary it'd probably be a good idea to flatten it into one dimension actually but I'll worry about that another time just out of curiosity I made a quick test to roughly measure the lookup speed of the dictionary we were using versus our custom approach so accessing the dictionary is taking 762 milliseconds and that's for many millions of lookups of course and then

00:38:52
 doing the same number of lookups with our magic bit board approach takes just 53 milliseconds so that's nice to see all right so all the slating pieces are now using the magic bit board approach and by sliding pieces I mean the Rooks Bishops in Queens I have updated the pawn moves to use bit boards as well although that just requires shifting some bits around there's no magic lookups involved there haven't actually fully tested the Pawn's move generation yet but I'm pretty confident it works

00:39:24
 okay never mind apparently it's completely broken it turns out what I missed is that pawns now have a new sneak attack where they can warp around the edge of the board and capture enemy pieces on the other side a pretty cool feature if you ask me makes more sense than unpleasant at least but I will sadly have to remove it okay so let's take a look at how much we've managed to actually improve the speed of the move generation in total running this full test Suite originally took around 22 seconds to complete and

00:39:55
 this old version used a list to storm moves so something I tried while I was testing all this bit board stuff is simply changing that to a fixed size array initialized with the maximum number of legal moves in any position which from a quick internet search appears to be this rather outlandish but technically possible position where white has 218 legal moves this change took running the test from 22 seconds down to 18. I then read some advice online about creating the move array using this stack

00:40:29
 airlock expression to avoid having the garbage collection poking its nose into our affairs this does make things a little clunky because instead of simply asking for the moves and receiving them nice and elegant we now first have to allocate some memory on the stack and then give that to the move generator to store the moves in the move generator will also then slice off the unused space because on average there are about 31 legal moves in a chess position not 218 so that ultimately we end up with just the

00:40:59
 actual moves I don't really love this code so I was a bit upset to see the test time go from 18 seconds down to around 15 and a half I guess I'll just have to learn to live with it anyway the final thing of course with implementing all that magic bit board stuff and that has brought the time down again to around nine and a half seconds let's find out now if this faster move generation actually translates to playing any better so against the previous version it is scored 447 wins to 275 losses which is not too bad and

00:41:33
 against version 1 we're now getting 792 wins to 89 losses honestly we probably could have made bigger improvements focusing all this time on other areas but I feel like I learned quite a lot from the process so I can't complain too much anyway let's just try a few more quick things before we call it a day one thing I've been tinkering with is the order that moves the satchden for example captures used to be ranked purely by the difference in the value of the pieces involved so we'd consider capturing a

00:42:05
 queen with a pawn before we'd consider capturing a pawn with a queen which makes sense but now I am also using this bit Board of squares that the enemy attacks which is created for detecting checks during move generation to make a reasonable guess about whether the opponent can recapture the piece on the next move and obviously if they're not able to then that's generally preferable another thing I've been experimenting with here is a technique called killer moves the idea is that inside of the

00:42:34
 search whenever we encounter a move that's so good it causes us to reject the current line of the search we record it as a killer move and so for the rest of the search even though we're not looking at the exact same position anymore if it's still possible to play the killer move we'll give it a high rank because there's a chance that it's still really good just as a slightly simplified example in this position if white plays Bishop takes Bishop Black's best response is

00:43:01
 Queen D1 checkmate If instead white captures the bishop with the Knight Black's best move is still checkmate and if instead y captures the bishop with the queen well you get the picture Queen D1 is a very good move in many variations of this position so by giving a priority in the search we can more quickly reject White's bad moves and hopefully find something that actually does defend against the threat okay let's see how this does so against the previous version we have 477 wins to

00:43:34
 221 losses pretty good and against version 1 we're now scoring 851 wins to 51 losses another technique that ties into what we've been doing is something called late move reductions the idea is that if our little move ordering scheme is working well then the best move should be among the first few moves that we search at least most of the time so once we've finished with those first few moves we're going to search the remaining moves at a shallower depth because we assume they're probably not

00:44:08
 very good however if the evaluation turns out to be better than everything we've looked at so far then we will have to search that move again at the full depth to get a more reliable evaluation hopefully though those repeated searches will be infrequent enough to still speed things up overall and hopefully that increased speed will outweigh the danger of the reduced such mistakenly thinking that a good move is bad just because it couldn't see far enough ahead that's a lot of hoping so let's see if

00:44:39
 it works out against the previous version we're getting 397 wins to 238 losses which I'm happy to see and against version 1 we're now up to 873 wins to just 26 losses now I've been idly watching some of these Test games as they whiz past and I happen to notice something a bit concerning every now and again the program would be completely winning but instead of making progress it would just Shuffle back and forth until the game ended in a draw full amount of debugging I finally realized that this is probably because

00:45:18
 I'm only testing for repetitions against positions that have actually occurred in the game whereas I should also include positions that occur inside of the search so I've just made a crude little repetition table that handles that I've then tested it against version 1 to see if that fixes the issue and it at least seems to be helping a lot because we're now getting 898 wins to 27 losses with the number of draws coming down from 101 to just 75. I would really like to beat the original version 100 of the

00:45:50
 time but I'm going to leave that goal for the future because I'm beginning to see chess pieces in my dreams at this point [Music] laughs but first I do want to get this little butt running on Lee chess so we can get an estimate of how good it is to begin with we need to convert our chess program which is running inside of the unity game engine to a simple console application I'm only really using Unity for rendering these cutting-edge Graphics we have going here so converting it is as simple as just

00:46:20
 taking this folder of core scripts and dragging it into a visual studio project and then just deleting the occasional unityengine.debug.log sprinkled throughout the files now in this main function we'll just keep looping until a quick command is received from the console and simply forward any other console messages to the engine I've then written an extremely crude and incomplete implementation of the universal chess interface which is a protocol for communicating with chess engines so the communication between us

00:46:51
 and Lee chess is going to go something like this leeches will say UCI and we'll respond UCI okay liches will then say UCI new game followed by is ready and we'll say ready okay then leeches will tell us to set up the stat position and give the go command followed by the amount of time remaining for white and black in milliseconds we'll then figure out what move we want to make and respond with this notation simply the square we want to move from followed by the square we want to move

00:47:21
 to once the opponent has responded leeches will send a new position command and give us a list of the moves played in the game so far then another go command with the updated times to which we'll respond with the next move we want to make and so on it goes so let's now create a luchess account to play on and I think I'll simply call it the coding Adventure bot I agree that I will at no time receive assistance from a chess computer okay but what if I am a chess computer checkmate alright I have generated an

00:47:56
 authorization tokens that we can interact with the API and I'll then just run a little command to tell it to upgrade our account to a bot account if we visit the website now we can see there's a cute little robot icon over here and also a big bot label next to our name so everyone knows that we're not human now a little robot's actually not going to be talking to leeches directly but rather I'm going to use this super helpful python repository to act as our go-between so after downloading that all

00:48:27
 we need to do is drag the compiled chess program into the engines folder and then open the config file and in there we just put our super secret access token and specify the path to the chess engine we can also customize all sorts of settings such as whether our bot can play variants like anti-chess Atomic and so on which it sadly can't although that might be fun to add at some point then just for the first few days I think I'll restrict the time controls to bulletin Blitz Games only just so that

00:48:58
 it can hopefully get a chance to play lots of different opponents that means that the slowest time control would be something like 5 minutes per side with a 4 second increment I'll also turn off matches against other Bots for the moment because I'm most interested in seeing how it fares against humans so if everything's been set up correctly we should be able to fire it up by just launching the leeches botch python script and it looks like we're live now Albert can't actually challenge humans

00:49:25
 that it'd probably be really annoying for them so I'm going to post about it online and hopefully some people will be in the mood to play in the meantime I'd like to try playing a game myself just for fun I'm going to put our Bots evaluation of the current position up on the screen along with the obviously far more accurate evaluation of stockfish now being able to see what stockfish thinks the best move is might influence me a little so I've engineered a high-tech solution allowing you to see

00:49:52
 what it thinks while keeping me in the dark okay let's get this game started we're playing 10 minutes per side with no increment I'm gonna try being very aggressive usually not a wise strategy against computers but I think the weakest part of the engine is still how it evaluates King safety which is to say not at all so I think it might make some sense to just throw all our pawns at the king and hope something happens in hindsight I probably should have prioritized working on that aspect of

00:50:21
 the evaluation but I got so sidetracked with all the bit board stuff so I may need to subject you all to a chess part 3 in the future apologies in advance all right I think I'm going to Castle queenside here I like that our Rook lands opposite the queen which should gain us some time and then let's continue storming up with the pawns uh what is what is this so if we take the hanging Knight there's Knight check and then wherever we move the king is going to be Checkmate that's devious so let's let's do this instead

00:50:59
 okay Knight takes uh aren't we winning a piece because if we take with the pawn then the Knight is pinned by The Rook oh no there's there's Queen check here to get out of it so Queen takes instead then if Knight check here we can take with the queen to protect the Rook so we don't get mated and in the case of the other check uh we have Bishop takes protecting The Rook so this should be fine okay the Queen's now attacking the other Rook so I'd like to move the bishop out of the way it can only really go here

00:51:32
 but then if the pawn attacks it we'll have to retreat and then might check here is not gonna be a good time so I guess we need to move the Rook instead all right so I need to rescue The Rook again and I assume the Pawn's going to protect the Knight and also uncover an attack on our Queen so let's save her as well and I think we better take this because we're kind of running out of Safe squares to even put the queen at this point I am a little worried about this Pawn here but we can maybe pin it to the

00:52:02
 queen with the bishop and try hunted down actually don't do that because of this so let's First Take the Pawn's gonna go one forward and then let's finally bring the bishop out okay so Black's attacking this Pawn I'm thinking maybe counter-attacking the bishop and then if the Rook defends we can take this Pawn because the bishop is well I was gonna say it's pinned but actually there's check here so scratch that maybe we just move the pawn one up then I want to get back to charging these

00:52:39
 pawns off the board I feel like our plans were derailed so much but I think we can resume our attack hold on I'm about to blunder this bishop check again okay but now our attack is officially back on this is suddenly starting to look really promising actually black does have the annoying past Pawn but the king is very exposed like maybe we bring the bishop out here and then we can start checking with the Rook [Music] okay I'm very tempted to bring the Rook up here there is Queen check King here

00:53:15
 Queen takes uh what if we just keep running though so King here this seems pretty dangerous but also kind of interesting I'm gonna try it [Music] okay that's an annoying move I failed to consider stopping all of our checks but what if Queen here if the pawn pushes which feels like Black's main threat that is just meeting two so black would maybe need to respond by dropping the queen back something like this might be good then but time's running low we've got to go fast oh I kind of forgotten about my king

00:53:52
 already so Pawn takes Queen check King here Queen check this is getting confusing if we run up immediately with the King instead no there's no way we're surviving that I think we have to take Queen check now we have to go here oh and that sequence removed the defender of our Bishop that's unfortunately very smart okay but Queen here threatens mate on G8 and if the queen takes the bishop then we have mate on G7 but the Rook can just take the bishop instead so the queen defends G7 oh no

00:54:27
 we probably have to sacrifice The Rook although there is still Bishop here threatening meat at least okay we're gonna get checked a million times you could have to come hide on the other side of the board there goes the bishop but let's see if we can give some checks at least no we're still the ones getting jacked of course I'm really regretting my choices [Music] okay good game computer the last time we played I felt like I still had an edge over the engine but it definitely seems better than me now

00:54:59
 which I have mixed feelings about anyway we have had some activity in the console in the meanwhile so it looks like someone took up The Challenge online let's see if they've had any luck our butt played white in this last game and it looks like it managed to build a slight Advantage out of the opening before losing it all by choosing the wrong direction to Castle according to stockfish now we have an endgame that's slightly worse for white on the count of Black's control over the open file and this week

00:55:32
 double pawns I guess aren't helping either black slipped up a little here though in trying to put pressure on this Pawn because white can simply defend it and now the Rook is actually stuck in this little cubby hole the king urgently needs to come around to defend the Rook from B3 but a few moves later and it's too late defending from this square is not going to work because the bot is able to swing The Rook around the back to Chase the king away leaving the rook undefended and a few moves later we have checkmate

00:56:08
 so thank you to the opponent for playing and while we're waiting for some more games I'm curious to see how the bot fares in a match against stockfish itself so I ran a match for 100 games the result of which was unsurprisingly Zero wins zero draws and a hundred losses okay we're getting crushed so let's get our Revenge by taking out the fish's Queen in a 100 game match with no Queen stockfish was actually still able to win twice which is a little scary I'll give the queen back though because

00:56:41
 maybe there was a little hash and for our last test let's take away just a single Rook instead and the result this time is 31 wins eight draws and 61 losses so if there's one thing our little creation isn't lacking it's room for improvement anyway over the last few days it's played 270 games online although only a fraction of those have been ranked games so the ratings are still extremely uncertain right now though it's just under 2300 Blitz which is roughly what I would have

00:57:14
 estimated so I'm very curious to see if it remains in that region or changes dramatically for anyone unfamiliar with leeches ratings a rough reference is that a total beginner is around 600 the average player is around 1500 and the best humans in the world are just above 3000. so I'll be keeping an eye on the blitz rating and as for bullet that is all the way up at 2600. my guess is that that's a bit higher than it deserves because I have had the dubious pleasure of being obliterated in

00:57:46
 Bullet by players at that rating and it felt a lot more hopeless playing against them than it does playing against the botch for example here's a bullet game I played against it where I sacrificed a rook to destroy the pawn cover around its King The Botch is pretty pleased with its position at this point since it has an extra piece but to humanize and fish eyes of course White's vulnerable King is much more important than the extra Rook busy doing absolutely nothing in the corner here so I think that player is better than me

00:58:15
 could probably exploit this king's safety obliviousness to win a lot of games quite quickly I on the other hand ended up missing a painfully obvious Maiden 2 and lost the game of course if the bot doesn't appreciate the safety of its own King it also can't properly judge attacks on the enemy King so here's an interesting game it played online where back to back to back blunders left it with a very good position but now instead of realizing how this Knight in combination with the bishop

00:58:46
 and threats of the pawn promoting or The Rook swooping in have the white king and a serious pickle it decided to just grab this Pawn with the Knight and then wander off on some sort of side quest to harass The Rook white was then able to launch a swift counter-attack against Black's King and ultimately trap it in a Perpetual check to rescue the game so I feel like this bullet rating might go down a bit with time maybe to around 2450 is my prediction anyway if you'd like to play the bot yourself I'll leave a link to its page

00:59:20
 and you can simply click the little swords to send a challenge or the little TV to watch if anyone else is currently playing in any case I will leave you with a game between our coding Adventure watch and stockfish 15. alright thanks for watching and until next time cheers [Music] [Music] foreign [Music] [Music] [Music]

